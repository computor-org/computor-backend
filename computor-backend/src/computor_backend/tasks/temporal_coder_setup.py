"""
Temporal workflows for Coder workspace image building and template management.

These workflows replace the docker-compose init services (coder-image-builder-*,
coder-template-setup) with admin-triggered operations via API endpoints.

Templates are discovered dynamically from the templates directory. Each template
directory must contain a `template.json` manifest with:
  - coder_template_name: Name used in Coder (e.g. "python-workspace")
  - image_name: Docker image name (e.g. "computor-workspace-python3.13")
  - build_args_env: List of env var names to pass as Docker build args (optional)
  - display_name / description / icon: Template display metadata PATCHed into
    Coder after each push; the web UI renders these. Icon is a Coder built-in
    path like "/icon/python.svg" or an absolute URL. (optional)
"""
import asyncio
import json
import logging
import os
import re
import subprocess
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from .registry import register_task
from .temporal_base import BaseWorkflow, WorkflowResult
from .worker_settings import get_worker_settings

logger = logging.getLogger(__name__)

# Versioned workspace image tags kept per repo by the cleanup activity: the
# tag just pinned by the template push plus rollback targets. Older versions
# are untagged on the build host and deleted from the registry.
IMAGE_VERSIONS_TO_KEEP = 2

# Auto-generated tag shape ("v" + workflow.now timestamp). Only tags matching
# this are ever cleanup candidates — :latest, admin-chosen custom tags and
# foreign repos are never touched.
_VERSION_TAG_RE = re.compile(r"^v\d{8}-\d{6}$")

_REGISTRY_REPO_ROOT = "/var/lib/registry/docker/registry/v2/repositories"


def _stale_version_tags(tags: List[str]) -> List[str]:
    """Versioned tags beyond the newest IMAGE_VERSIONS_TO_KEEP.

    Fixed-width timestamps make lexical order chronological.
    """
    versioned = sorted((t for t in tags if _VERSION_TAG_RE.match(t)), reverse=True)
    return versioned[IMAGE_VERSIONS_TO_KEEP:]


def _discover_templates(templates_dir: str) -> Dict[str, Dict[str, Any]]:
    """
    Scan the templates directory for subdirectories containing template.json.

    Returns a dict keyed by directory name (template key) with manifest contents.
    """
    templates = {}
    if not os.path.isdir(templates_dir):
        logger.warning(f"Templates directory does not exist: {templates_dir}")
        return templates

    for entry in sorted(os.listdir(templates_dir)):
        manifest_path = os.path.join(templates_dir, entry, "template.json")
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)
                manifest["dir_name"] = entry
                templates[entry] = manifest
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to read {manifest_path}: {e}")

    return templates


def _resolve_templates(
    requested: Optional[List[str]], templates_dir: str
) -> List[Dict[str, Any]]:
    """
    Resolve which templates to process.

    requested=None means all discovered templates.
    Requested names are matched against both the directory name (key) and
    the coder_template_name from the manifest.
    """
    discovered = _discover_templates(templates_dir)
    if not discovered:
        return []

    if requested is None:
        return list(discovered.values())

    results = []
    for name in requested:
        # Match by directory name or coder_template_name
        for key, info in discovered.items():
            if key == name or info.get("coder_template_name") == name:
                results.append(info)
                break

    return results


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


@activity.defn(name="build_workspace_image")
def build_workspace_image(
    template_key: str,
    templates_dir: str,
    registry_host: str,
    image_tag: str = "latest",
) -> Dict[str, Any]:
    """
    Build a workspace Docker image and push it to the local registry.

    BLOCKING activity: the Docker SDK build/push is a synchronous, multi-minute
    operation, so this is a plain ``def`` that Temporal runs in the worker's
    thread pool (Worker(activity_executor=...)) instead of on the event loop.

    Pushes two tags: the moving ``:latest`` and an immutable ``:<image_tag>``.
    The versioned tag is what a Coder template version pins to, so rebuilt
    workspaces actually pull the new image (a moved ``:latest`` would not be
    re-pulled by the docker provider's ``keep_locally`` image resource) and a
    rollback target exists.

    Uses the Docker SDK (already a dependency) to build and push.
    """
    import docker as docker_sdk

    # Discover template from filesystem
    discovered = _discover_templates(templates_dir)
    info = discovered.get(template_key)
    if not info:
        return {"success": False, "template": template_key, "error": f"Unknown template: {template_key}"}

    # Prefer the worker's own env vars (docker network) over parameters from the backend
    settings = get_worker_settings()
    if settings.coder_registry_host is not None:
        registry_host = settings.coder_registry_host

    build_dir = os.path.join(templates_dir, info["dir_name"])
    dockerfile_path = os.path.join(build_dir, "Dockerfile")

    if not os.path.isfile(dockerfile_path):
        logger.warning(f"No Dockerfile found at {dockerfile_path}, skipping {template_key}")
        return {"success": True, "template": template_key, "skipped": True, "reason": "No Dockerfile"}

    repo = f"{registry_host}/{info['image_name']}"
    # Always publish :latest; add the versioned tag when it is distinct.
    push_tags = ["latest"]
    if image_tag and image_tag != "latest":
        push_tags.append(image_tag)

    # Collect build args from environment variables
    buildargs = {}
    for env_name in info.get("build_args_env", []):
        val = os.environ.get(env_name)
        if val:
            buildargs[env_name] = val

    logger.info(
        f"Building image {repo} tags={push_tags} from {build_dir}"
        + (f" (build_args: {list(buildargs.keys())})" if buildargs else "")
    )

    try:
        client = docker_sdk.DockerClient(base_url="unix://" + settings.docker_socket_path)

        # Build (tagged with the first tag), then apply the remaining tags to the
        # same image id so every tag is byte-identical.
        image, build_logs = client.images.build(
            path=build_dir, tag=f"{repo}:{push_tags[0]}", rm=True, buildargs=buildargs or None
        )
        for chunk in build_logs:
            if "stream" in chunk:
                line = chunk["stream"].strip()
                if line:
                    logger.info(f"[build:{template_key}] {line}")

        for extra in push_tags[1:]:
            image.tag(repo, tag=extra)

        # Push every tag
        for t in push_tags:
            push_output = client.images.push(repo, tag=t)
            logger.info(f"Push output for {template_key} ({repo}:{t}): {push_output}")

        return {
            "success": True,
            "template": template_key,
            "image": f"{repo}:{image_tag}",
            "tags": push_tags,
        }

    except Exception as e:
        logger.exception(f"Failed to build/push image for {template_key}")
        return {"success": False, "template": template_key, "error": str(e)}


@activity.defn(name="cleanup_stale_workspace_images")
def cleanup_stale_workspace_images(
    template_keys: List[str],
    templates_dir: str,
    registry_host: str,
) -> Dict[str, Any]:
    """
    Prune superseded versioned workspace images after a successful build+push.

    Every build run mints a fresh ``vYYYYMMDD-HHMMSS`` tag, so without pruning
    the build host's docker daemon and the local registry each grow by one
    image generation (multi-GB for MATLAB) per rebuild. For each processed
    template's repo this keeps ``:latest`` plus the IMAGE_VERSIONS_TO_KEEP
    newest versioned tags and removes the rest:

    * on the host daemon by untagging — an image whose last tag is held by a
      container docker refuses to delete, so in-use images survive;
    * in the registry by removing stale tag directories via exec in the
      registry container (its HTTP API is unreachable from the worker — the
      registry is deliberately network-isolated), then one
      ``registry garbage-collect --delete-untagged`` pass to reclaim blobs.

    Only safe once template pushes have re-pinned every processed template to
    this run's tag, and while no other build is pushing (GC racing a push can
    drop fresh blobs) — both hold as the final activity of the push workflow,
    whose task queue processes activities sequentially.

    BLOCKING activity (docker SDK), plain ``def`` for the worker thread pool.
    Best-effort by design: always returns a result dict, never raises.
    """
    import docker as docker_sdk

    settings = get_worker_settings()
    if settings.coder_registry_host is not None:
        registry_host = settings.coder_registry_host

    discovered = _discover_templates(templates_dir)
    image_names = [
        discovered[k]["image_name"] for k in template_keys if k in discovered
    ]

    removed_local: Dict[str, List[str]] = {}
    removed_registry: Dict[str, List[str]] = {}
    skipped: List[str] = []
    errors: List[str] = []

    try:
        client = docker_sdk.DockerClient(base_url="unix://" + settings.docker_socket_path)
    except Exception as e:
        return {"success": False, "error": f"docker connect failed: {e}"}

    # Host daemon: untag stale versions. The image itself disappears with its
    # last tag unless a container still references it (docker then 409s).
    for name in image_names:
        repo = f"{registry_host}/{name}"
        try:
            tags = [
                t.rsplit(":", 1)[1]
                for img in client.images.list(name=repo)
                for t in img.tags
                if t.startswith(repo + ":")
            ]
        except Exception as e:
            errors.append(f"{repo}: list failed: {e}")
            continue
        for tag in _stale_version_tags(tags):
            try:
                client.images.remove(image=f"{repo}:{tag}")
                removed_local.setdefault(name, []).append(tag)
            except Exception as e:
                skipped.append(f"{repo}:{tag}: {e}")

    # Registry: drop stale tag references, then garbage-collect blobs.
    gc_summary = None
    try:
        registry = client.containers.get(settings.coder_registry_container)
    except Exception as e:
        registry = None
        errors.append(
            f"registry container {settings.coder_registry_container!r} unavailable: {e}"
        )

    if registry is not None:
        stale_dirs = []
        for name in image_names:
            tags_dir = f"{_REGISTRY_REPO_ROOT}/{name}/_manifests/tags"
            code, out = registry.exec_run(["ls", "-1", tags_dir])
            if code != 0:
                continue  # repo not (yet) in the registry
            for tag in _stale_version_tags(out.decode(errors="replace").split()):
                stale_dirs.append(f"{tags_dir}/{tag}")
                removed_registry.setdefault(name, []).append(tag)
        if stale_dirs:
            code, out = registry.exec_run(["rm", "-rf", *stale_dirs])
            if code != 0:
                errors.append(
                    f"registry tag removal failed: {out.decode(errors='replace')[:300]}"
                )
            else:
                # Removing a tag dir only unlinks the reference; GC deletes the
                # now-untagged manifests and any blobs no manifest uses.
                code, out = registry.exec_run(
                    ["registry", "garbage-collect", "--delete-untagged",
                     "/etc/docker/registry/config.yml"]
                )
                tail = out.decode(errors="replace").strip().splitlines()[-3:]
                gc_summary = f"exit={code}: " + " | ".join(tail)
                if code != 0:
                    errors.append(f"registry GC failed: {gc_summary}")

    result = {
        "success": not errors,
        "removed_local": removed_local,
        "removed_registry": removed_registry,
        "skipped_in_use": skipped,
        "gc": gc_summary,
    }
    if errors:
        result["errors"] = errors
    logger.info(f"Workspace image cleanup: {result}")
    return result


def _template_declares_variable(template_dir: str, name: str) -> bool:
    """True if any .tf file in the template declares `variable "<name>"`.

    `coder templates push --variable` rejects variables the template does not
    declare, so deployment-wide-but-template-specific values (e.g. the MATLAB
    license) must only be passed to templates that opt in by declaring them.
    """
    needle = f'variable "{name}"'
    try:
        entries = os.listdir(template_dir)
    except OSError:
        return False
    for fn in entries:
        if not fn.endswith(".tf"):
            continue
        try:
            with open(os.path.join(template_dir, fn), "r", encoding="utf-8") as f:
                if needle in f.read():
                    return True
        except OSError:
            continue
    return False


@activity.defn(name="push_coder_template")
async def push_coder_template(
    template_key: str,
    templates_dir: str,
    coder_url: str,
    coder_admin_email: str,
    coder_admin_password: str,
    backend_internal_url: str,
    backend_external_url: str,
    dev_forward_ports: str,
    ttl_ms: int,
    activity_bump_ms: int,
    registry_host: str = "localhost:5000",
    image_tag: str = "latest",
    template_variables: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Push a Coder template (Terraform config) using the coder CLI,
    then set TTL via the Coder REST API.

    Pins the template's ``workspace_image`` variable to the immutable
    ``<registry>/<image>:<image_tag>`` ref so this new template version is tied
    to a specific image build (and so rolling workspaces onto it actually
    changes the running image). ``registry_host`` here is the provisioner's view
    of the registry (matches the template's default host), NOT the worker's push
    host, so it is intentionally not overridden by CODER_REGISTRY_HOST.

    MIXED activity: the network I/O (Coder login + template GET/PATCH via
    CoderClient) stays on the event loop; only the bounded-but-blocking
    ``coder templates push`` subprocess is offloaded with asyncio.to_thread so
    it does not stall the loop while the CLI runs (up to 300s).
    """
    from computor_backend.coder.client import CoderClient
    from computor_backend.coder.config import CoderSettings

    # Discover template from filesystem
    discovered = _discover_templates(templates_dir)
    info = discovered.get(template_key)
    if not info:
        return {"success": False, "template": template_key, "error": f"Unknown template: {template_key}"}

    template_dir = os.path.join(templates_dir, info["dir_name"])
    main_tf = os.path.join(template_dir, "main.tf")

    if not os.path.isfile(main_tf):
        logger.warning(f"No main.tf at {main_tf}, skipping {template_key}")
        return {"success": True, "template": template_key, "skipped": True, "reason": "No main.tf"}

    coder_template_name = info["coder_template_name"]

    # Prefer the worker's own CODER_URL env var (docker network) over the
    # parameter passed from the backend (which may be localhost).
    coder_url_override = get_worker_settings().coder_url
    if coder_url_override is not None:
        coder_url = coder_url_override

    image_ref = f"{registry_host}/{info['image_name']}:{image_tag}"

    # Route login and template GET/PATCH through CoderClient instead of raw
    # httpx. The client is configured with this activity's resolved url and
    # admin credentials (its default org-scoped template endpoints match the
    # raw calls this used to make, and carry only the Coder-Session-Token
    # header — no X-Admin-Secret — exactly as before).
    settings = CoderSettings(
        url=coder_url,
        admin_email=coder_admin_email,
        admin_password=coder_admin_password,
    )

    async with CoderClient(settings=settings) as client:
        # Step 1: get session token via API login
        logger.info(f"Logging in to Coder at {coder_url} as {coder_admin_email}")
        try:
            session_token = await client._get_session_token()
        except Exception as e:
            return {"success": False, "template": template_key, "error": f"Coder login failed: {e}"}

        # Step 2: push template via coder CLI (needs the raw session token)
        env = os.environ.copy()
        env["CODER_SESSION_TOKEN"] = session_token
        env["CODER_URL"] = coder_url

        cmd = [
            "coder", "templates", "push", coder_template_name,
            "--directory", template_dir,
            "--variable", f"computor_backend_internal={backend_internal_url}",
            "--variable", f"computor_backend_url={backend_external_url}",
            "--variable", f"dev_forward_ports={dev_forward_ports}",
            "--variable", f"workspace_image={image_ref}",
        ]
        # Optional deployment-wide variables (e.g. the MATLAB license) are
        # applied only to templates that declare them — `coder templates push`
        # rejects undeclared variables. See _template_declares_variable.
        for name, value in (template_variables or {}).items():
            if value and _template_declares_variable(template_dir, name):
                cmd += ["--variable", f"{name}={value}"]
        cmd += ["--yes"]
        logger.info(f"Running: {' '.join(cmd)}")

        try:
            # Offload the blocking coder CLI subprocess to a thread so the
            # worker's event loop keeps servicing other activities/heartbeats.
            result = await asyncio.to_thread(
                subprocess.run,
                cmd, capture_output=True, text=True, timeout=300, env=env
            )
            if result.returncode != 0:
                logger.error(f"coder templates push failed: {result.stderr}")
                return {
                    "success": False,
                    "template": template_key,
                    "error": f"coder templates push failed (rc={result.returncode}): {result.stderr}",
                }
            logger.info(f"Template {coder_template_name} pushed successfully")
        except subprocess.TimeoutExpired:
            return {"success": False, "template": template_key, "error": "coder templates push timed out"}
        except FileNotFoundError:
            return {"success": False, "template": template_key, "error": "coder CLI not found on PATH"}

        # Step 3: set TTL + display metadata via REST API (through the client).
        # The manifest is the source of truth for display_name/description/icon,
        # so they are always sent ("" clears a previously-set value).
        try:
            template_id = (await client.get_template(coder_template_name))["id"]
            await client.patch_template_meta(
                template_id,
                ttl_ms=ttl_ms,
                activity_bump_ms=activity_bump_ms,
                display_name=info.get("display_name", ""),
                description=info.get("description", ""),
                icon=info.get("icon", ""),
            )
            logger.info(
                f"Meta set for {coder_template_name}: ttl={ttl_ms}ms, bump={activity_bump_ms}ms, "
                f"display_name={info.get('display_name', '')!r}"
            )
        except Exception as e:
            logger.warning(f"Template pushed but meta update failed for {template_key}: {e}")
            return {
                "success": True,
                "template": template_key,
                "warning": f"Template pushed but meta update failed: {e}",
            }

    return {
        "success": True,
        "template": template_key,
        "coder_template": coder_template_name,
        "image": image_ref,
    }


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


def _progress_templates(resolved: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "key": item["dir_name"],
            "name": item.get("coder_template_name", item["dir_name"]),
            "display_name": item.get("display_name"),
            "status": "pending",
            "phase": "queued",
            "error": None,
        }
        for item in resolved
    ]


def _update_template_progress(
    progress: Dict[str, Any], key: str, **changes: Any
) -> None:
    for item in progress.get("templates", []):
        if item.get("key") == key:
            item.update(changes)
            return


def _finish_progress(progress: Dict[str, Any], failed: int) -> None:
    progress["phase"] = "complete"
    progress["current_template"] = None
    progress["completed"] = progress.get("total", 0)
    progress["operation_status"] = (
        "completed_with_errors" if failed else "completed"
    )


@register_task
@workflow.defn(name="build_workspace_images", sandboxed=False)
class BuildWorkspaceImagesWorkflow(BaseWorkflow):
    """Workflow to build one or more workspace Docker images."""

    @classmethod
    def get_name(cls) -> str:
        return "build_workspace_images"

    @classmethod
    def get_task_queue(cls) -> str:
        return "coder-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=30)

    def __init__(self) -> None:
        self._progress: Dict[str, Any] = {
            "phase": "queued",
            "operation_status": "running",
            "templates": [],
            "current_template": None,
            "completed": 0,
            "total": 0,
        }

    @workflow.query
    def get_progress(self) -> Dict[str, Any]:
        return self._progress

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        templates_dir = parameters.get("templates_dir", "/templates")
        registry_host = parameters.get("registry_host", "localhost:5000")
        requested = parameters.get("templates")
        # One immutable image tag per run; workflow.now() is replay-deterministic.
        image_tag = parameters.get("image_tag") or ("v" + workflow.now().strftime("%Y%m%d-%H%M%S"))
        self._progress.update({"phase": "discovering", "image_tag": image_tag})

        # Discovery happens inside the activity (which runs on the worker).
        # The workflow just needs to know which keys to iterate over.
        # Pass templates_dir so activities can discover at runtime.
        resolved = parameters.get("_resolved_templates")
        if not resolved:
            resolved = await workflow.execute_activity(
                discover_template_operations,
                args=[templates_dir, requested],
                start_to_close_timeout=timedelta(seconds=30),
            )
        template_keys = [item["dir_name"] for item in resolved]

        if not template_keys:
            return WorkflowResult(
                status="failed",
                result=None,
                error="No valid templates found in " + templates_dir,
                metadata={"workflow_type": "build_workspace_images"},
            )

        self._progress.update({
            "phase": "building",
            "templates": _progress_templates(resolved),
            "total": len(template_keys),
        })

        workflow.logger.info(f"Building images for templates: {template_keys}")

        results = []
        for key in template_keys:
            self._progress.update({"phase": "building", "current_template": key})
            _update_template_progress(self._progress, key, status="running", phase="building")
            result = await workflow.execute_activity(
                build_workspace_image,
                args=[key, templates_dir, registry_host, image_tag],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            results.append(result)
            ok = bool(result.get("success"))
            _update_template_progress(
                self._progress,
                key,
                status="succeeded" if ok else "failed",
                phase="complete",
                error=result.get("error"),
                result=result,
            )
            self._progress["completed"] += 1

        failed = [r for r in results if not r.get("success")]
        _finish_progress(self._progress, len(failed))
        if failed:
            return WorkflowResult(
                status="completed_with_errors",
                result={"builds": results, "image_tag": image_tag},
                error=f"{len(failed)} build(s) failed",
                metadata={"workflow_type": "build_workspace_images"},
            )

        return WorkflowResult(
            status="completed",
            result={"builds": results, "image_tag": image_tag},
            metadata={"workflow_type": "build_workspace_images"},
        )


@register_task
@workflow.defn(name="push_coder_templates", sandboxed=False)
class PushCoderTemplatesWorkflow(BaseWorkflow):
    """Workflow to push Coder templates (optionally building images first)."""

    @classmethod
    def get_name(cls) -> str:
        return "push_coder_templates"

    @classmethod
    def get_task_queue(cls) -> str:
        return "coder-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=30)

    def __init__(self) -> None:
        self._progress: Dict[str, Any] = {
            "phase": "queued",
            "operation_status": "running",
            "templates": [],
            "current_template": None,
            "completed": 0,
            "total": 0,
        }

    @workflow.query
    def get_progress(self) -> Dict[str, Any]:
        return self._progress

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        templates_dir = parameters.get("templates_dir", "/templates")
        registry_host = parameters.get("registry_host", "localhost:5000")
        build_images = parameters.get("build_images", False)
        coder_url = parameters.get("coder_url", "http://coder:7080")
        coder_admin_email = parameters.get("coder_admin_email")
        coder_admin_password = parameters.get("coder_admin_password")
        backend_internal_url = parameters.get("backend_internal_url", "http://host.docker.internal:8000")
        backend_external_url = parameters.get("backend_external_url", "http://host.docker.internal:8000")
        dev_forward_ports = parameters.get("dev_forward_ports", "")
        template_variables = parameters.get("template_variables", {})
        ttl_ms = parameters.get("ttl_ms", 3600000)  # 1 hour default
        activity_bump_ms = parameters.get("activity_bump_ms", 3600000)
        # One immutable image tag for this run, shared by the build and the
        # template's pinned workspace_image. workflow.now() is replay-safe.
        image_tag = parameters.get("image_tag") or ("v" + workflow.now().strftime("%Y%m%d-%H%M%S"))
        self._progress.update({"phase": "discovering", "image_tag": image_tag})

        if not coder_admin_email or not coder_admin_password:
            return WorkflowResult(
                status="failed",
                result=None,
                error="coder_admin_email and coder_admin_password are required",
                metadata={"workflow_type": "push_coder_templates"},
            )

        requested = parameters.get("templates")

        # Discover available templates on the worker filesystem
        resolved = await workflow.execute_activity(
            discover_template_operations,
            args=[templates_dir, requested],
            start_to_close_timeout=timedelta(seconds=30),
        )
        template_keys = [item["dir_name"] for item in resolved]

        if not template_keys:
            return WorkflowResult(
                status="failed",
                result=None,
                error="No valid templates found in " + templates_dir,
                metadata={"workflow_type": "push_coder_templates"},
            )

        self._progress.update({
            "phase": "building" if build_images else "pushing",
            "templates": _progress_templates(resolved),
            "total": len(template_keys),
        })

        # Step 1: optionally build images
        build_results: Dict[str, Dict[str, Any]] = {}
        if build_images:
            workflow.logger.info(f"Building images before pushing templates: {template_keys}")
            for key in template_keys:
                self._progress.update({"phase": "building", "current_template": key})
                _update_template_progress(self._progress, key, status="running", phase="building")
                result = await workflow.execute_activity(
                    build_workspace_image,
                    args=[key, templates_dir, registry_host, image_tag],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5),
                        backoff_coefficient=2.0,
                        maximum_attempts=2,
                    ),
                )
                build_results[key] = result
                if result.get("success"):
                    _update_template_progress(
                        self._progress, key, status="pending", phase="pushing", result=result
                    )
                else:
                    _update_template_progress(
                        self._progress,
                        key,
                        status="failed",
                        phase="building",
                        error=result.get("error"),
                        result=result,
                    )
                    self._progress["completed"] += 1

        # Step 2: push templates
        workflow.logger.info(f"Pushing templates: {template_keys}")

        results = []
        for key in template_keys:
            build_result = build_results.get(key)
            if build_images and build_result and not build_result.get("success"):
                results.append({
                    "success": False,
                    "template": key,
                    "stage": "build",
                    "error": build_result.get("error", "Image build failed"),
                })
                continue
            self._progress.update({"phase": "pushing", "current_template": key})
            _update_template_progress(self._progress, key, status="running", phase="pushing")
            result = await workflow.execute_activity(
                push_coder_template,
                args=[
                    key,
                    templates_dir,
                    coder_url,
                    coder_admin_email,
                    coder_admin_password,
                    backend_internal_url,
                    backend_external_url,
                    dev_forward_ports,
                    ttl_ms,
                    activity_bump_ms,
                    registry_host,
                    image_tag,
                    template_variables,
                ],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            results.append(result)
            ok = bool(result.get("success"))
            _update_template_progress(
                self._progress,
                key,
                status="succeeded" if ok else "failed",
                phase="complete",
                error=result.get("error"),
                result=result,
            )
            self._progress["completed"] += 1

        # Step 3: prune superseded image versions, but only for templates this
        # run just re-pinned to its fresh tag. Never on build_images=False
        # (e.g. a rollback push pinning an older tag that pruning would treat
        # as stale). Best-effort — a cleanup failure must not fail the push.
        cleanup = None
        if build_images:
            pushed_ok = [
                key for key, r in zip(template_keys, results)
                if r.get("success") and not r.get("skipped") and r.get("stage") != "build"
            ]
            if pushed_ok:
                try:
                    self._progress.update({"phase": "cleanup", "current_template": None})
                    cleanup = await workflow.execute_activity(
                        cleanup_stale_workspace_images,
                        args=[pushed_ok, templates_dir, registry_host],
                        start_to_close_timeout=timedelta(minutes=10),
                        retry_policy=RetryPolicy(maximum_attempts=1),
                    )
                except Exception as e:
                    workflow.logger.warning(f"Image cleanup failed (non-fatal): {e}")

        failed = [r for r in results if not r.get("success")]
        _finish_progress(self._progress, len(failed))
        if failed:
            return WorkflowResult(
                status="completed_with_errors",
                result={"pushes": results, "image_tag": image_tag, "cleanup": cleanup},
                error=f"{len(failed)} push(es) failed",
                metadata={"workflow_type": "push_coder_templates"},
            )

        return WorkflowResult(
            status="completed",
            result={"pushes": results, "image_tag": image_tag, "cleanup": cleanup},
            metadata={"workflow_type": "push_coder_templates"},
        )


@activity.defn(name="rollout_template_workspaces")
async def rollout_template_workspaces(
    template_key: str,
    templates_dir: str,
) -> Dict[str, Any]:
    """Roll every workspace of one template onto its active version.

    Policy: enable automatic updates for every workspace (so stopped ones adopt
    the active version on their next start), and additionally issue an immediate
    update build for workspaces that are currently up. In-progress, stopped and
    failed workspaces are left to auto-update rather than being force-started.
    """
    from computor_backend.coder.client import CoderClient

    discovered = _discover_templates(templates_dir)
    info = discovered.get(template_key)
    if not info:
        return {"success": False, "template": template_key, "error": f"Unknown template: {template_key}"}
    coder_template_name = info["coder_template_name"]

    updated_now = 0
    auto_on_start = 0
    already_current = 0
    errors: List[str] = []

    try:
        async with CoderClient() as client:
            version_id = await client.get_template_active_version(coder_template_name)
            targets = [
                w for w in await client.list_all_workspaces()
                if w.template_name == coder_template_name
            ]

            for w in targets:
                try:
                    # Always enable auto-update so a stopped/failed workspace
                    # adopts this version on its next start.
                    if not await client.set_workspace_auto_update(w.id, True):
                        errors.append(f"{w.name}: could not enable automatic updates")
                        continue

                    if w.template_version_id == version_id:
                        already_current += 1
                        continue

                    status = w.latest_build_status.value if w.latest_build_status else ""
                    is_up = w.latest_build_transition == "start" and status in ("succeeded", "running")
                    if is_up:
                        if await client.update_workspace_to_version(w.id, version_id):
                            updated_now += 1
                        else:
                            errors.append(w.name)
                    else:
                        auto_on_start += 1
                except Exception as e:  # noqa: BLE001 - collect per-workspace failures
                    errors.append(f"{w.name}: {e}")

        return {
            "success": len(errors) == 0,
            "template": coder_template_name,
            "active_version": version_id,
            "targets": len(targets),
            "updated_now": updated_now,
            "auto_update_on_start": auto_on_start,
            "already_current": already_current,
            "errors": errors,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Rollout failed for {template_key}")
        return {"success": False, "template": template_key, "error": str(e)}


@register_task
@workflow.defn(name="rollout_workspaces", sandboxed=False)
class RolloutWorkspacesWorkflow(BaseWorkflow):
    """Roll existing workspaces onto their template's active version."""

    @classmethod
    def get_name(cls) -> str:
        return "rollout_workspaces"

    @classmethod
    def get_task_queue(cls) -> str:
        return "coder-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        return timedelta(minutes=40)

    def __init__(self) -> None:
        self._progress: Dict[str, Any] = {
            "phase": "queued",
            "operation_status": "running",
            "templates": [],
            "current_template": None,
            "completed": 0,
            "total": 0,
        }

    @workflow.query
    def get_progress(self) -> Dict[str, Any]:
        return self._progress

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        templates_dir = parameters.get("templates_dir", "/templates")
        requested = parameters.get("templates")
        self._progress["phase"] = "discovering"

        resolved = await workflow.execute_activity(
            discover_template_operations,
            args=[templates_dir, requested],
            start_to_close_timeout=timedelta(seconds=30),
        )
        template_keys = [item["dir_name"] for item in resolved]
        if not template_keys:
            return WorkflowResult(
                status="failed",
                result=None,
                error="No valid templates found in " + templates_dir,
                metadata={"workflow_type": "rollout_workspaces"},
            )

        self._progress.update({
            "phase": "rolling_out",
            "templates": _progress_templates(resolved),
            "total": len(template_keys),
        })

        results = []
        for key in template_keys:
            self._progress.update({"phase": "rolling_out", "current_template": key})
            _update_template_progress(
                self._progress, key, status="running", phase="rolling_out"
            )
            result = await workflow.execute_activity(
                rollout_template_workspaces,
                args=[key, templates_dir],
                start_to_close_timeout=timedelta(minutes=20),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            results.append(result)
            ok = bool(result.get("success"))
            _update_template_progress(
                self._progress,
                key,
                status="succeeded" if ok else "failed",
                phase="complete",
                error=result.get("error") or ("; ".join(result.get("errors", [])) or None),
                result=result,
            )
            self._progress["completed"] += 1

        failed = [r for r in results if not r.get("success")]
        _finish_progress(self._progress, len(failed))
        return WorkflowResult(
            status="completed_with_errors" if failed else "completed",
            result={"rollouts": results},
            error=(f"{len(failed)} rollout(s) had errors" if failed else None),
            metadata={"workflow_type": "rollout_workspaces"},
        )


@activity.defn(name="discover_template_keys")
async def discover_template_keys(
    templates_dir: str,
    requested: Optional[List[str]],
) -> List[str]:
    """
    Lightweight activity to discover template keys on the worker filesystem.

    Workflows run in a sandbox and can't do filesystem I/O directly,
    so this activity handles the discovery.
    """
    templates = _resolve_templates(requested, templates_dir)
    return [t["dir_name"] for t in templates]


@activity.defn(name="discover_template_operations")
async def discover_template_operations(
    templates_dir: str,
    requested: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """Discover serializable template identity/label data for progress UIs."""
    return [
        {
            "dir_name": item["dir_name"],
            "coder_template_name": item.get("coder_template_name", item["dir_name"]),
            "display_name": item.get("display_name"),
        }
        for item in _resolve_templates(requested, templates_dir)
    ]


ACTIVITIES = [
    build_workspace_image,
    cleanup_stale_workspace_images,
    discover_template_keys,
    discover_template_operations,
    push_coder_template,
    rollout_template_workspaces,
]
