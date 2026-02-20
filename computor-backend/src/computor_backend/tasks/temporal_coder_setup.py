"""
Temporal workflows for Coder workspace image building and template management.

These workflows replace the docker-compose init services (coder-image-builder-*,
coder-template-setup) with admin-triggered operations via API endpoints.
"""
import logging
import os
import subprocess
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from .registry import register_task
from .temporal_base import BaseWorkflow, WorkflowResult

logger = logging.getLogger(__name__)

# Template name → directory name + registry image name mapping
TEMPLATE_REGISTRY = {
    "python3.13": {
        "dir_name": "python3.13",
        "image_name": "computor-workspace-python3.13",
        "coder_template_name": "python-workspace",
    },
    "matlab": {
        "dir_name": "matlab",
        "image_name": "computor-workspace-matlab",
        "coder_template_name": "matlab-workspace",
    },
}


def _get_all_template_keys() -> List[str]:
    """Get all registered template keys."""
    return list(TEMPLATE_REGISTRY.keys())


def _resolve_templates(requested: Optional[List[str]]) -> List[str]:
    """Resolve template list — None means all templates."""
    if requested is None:
        return _get_all_template_keys()
    return [t for t in requested if t in TEMPLATE_REGISTRY]


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


@activity.defn(name="build_workspace_image")
async def build_workspace_image(
    template_key: str,
    templates_dir: str,
    registry_host: str,
) -> Dict[str, Any]:
    """
    Build a workspace Docker image and push it to the local registry.

    Uses the Docker SDK (already a dependency) to build and push.
    """
    import docker as docker_sdk

    info = TEMPLATE_REGISTRY.get(template_key)
    if not info:
        return {"success": False, "template": template_key, "error": f"Unknown template: {template_key}"}

    # Prefer the worker's own env vars (docker network) over parameters from the backend
    registry_host = os.environ.get("CODER_REGISTRY_HOST", registry_host)

    build_dir = os.path.join(templates_dir, info["dir_name"])
    dockerfile_path = os.path.join(build_dir, "Dockerfile")

    if not os.path.isfile(dockerfile_path):
        logger.warning(f"No Dockerfile found at {dockerfile_path}, skipping {template_key}")
        return {"success": True, "template": template_key, "skipped": True, "reason": "No Dockerfile"}

    tag = f"{registry_host}/{info['image_name']}:latest"
    logger.info(f"Building image {tag} from {build_dir}")

    try:
        client = docker_sdk.DockerClient(base_url="unix:///var/run/docker.sock")

        # Build
        image, build_logs = client.images.build(path=build_dir, tag=tag, rm=True)
        for chunk in build_logs:
            if "stream" in chunk:
                line = chunk["stream"].strip()
                if line:
                    logger.info(f"[build:{template_key}] {line}")

        # Push
        push_output = client.images.push(registry_host + "/" + info["image_name"], tag="latest")
        logger.info(f"Push output for {template_key}: {push_output}")

        return {"success": True, "template": template_key, "image": tag}

    except Exception as e:
        logger.exception(f"Failed to build/push image for {template_key}")
        return {"success": False, "template": template_key, "error": str(e)}


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
) -> Dict[str, Any]:
    """
    Push a Coder template (Terraform config) using the coder CLI,
    then set TTL via the Coder REST API.
    """
    import httpx

    info = TEMPLATE_REGISTRY.get(template_key)
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
    coder_url = os.environ.get("CODER_URL", coder_url)

    # Step 1: get session token via API login
    logger.info(f"Logging in to Coder at {coder_url} as {coder_admin_email}")
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            login_resp = await http.post(
                f"{coder_url}/api/v2/users/login",
                json={"email": coder_admin_email, "password": coder_admin_password},
            )
            login_resp.raise_for_status()
            session_token = login_resp.json()["session_token"]
    except Exception as e:
        return {"success": False, "template": template_key, "error": f"Coder login failed: {e}"}

    # Step 2: push template via coder CLI
    env = os.environ.copy()
    env["CODER_SESSION_TOKEN"] = session_token
    env["CODER_URL"] = coder_url

    cmd = [
        "coder", "templates", "push", coder_template_name,
        "--directory", template_dir,
        "--variable", f"computor_backend_internal={backend_internal_url}",
        "--variable", f"computor_backend_url={backend_external_url}",
        "--variable", f"dev_forward_ports={dev_forward_ports}",
        "--yes",
    ]
    logger.info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
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

    # Step 3: set TTL via REST API
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            headers = {"Coder-Session-Token": session_token}

            # Get template ID
            tmpl_resp = await http.get(
                f"{coder_url}/api/v2/organizations/default/templates/{coder_template_name}",
                headers=headers,
            )
            tmpl_resp.raise_for_status()
            template_id = tmpl_resp.json()["id"]

            # PATCH TTL settings
            patch_resp = await http.patch(
                f"{coder_url}/api/v2/templates/{template_id}",
                headers=headers,
                json={"default_ttl_ms": ttl_ms, "activity_bump_ms": activity_bump_ms},
            )
            patch_resp.raise_for_status()
            logger.info(f"TTL set for {coder_template_name}: default={ttl_ms}ms, bump={activity_bump_ms}ms")

    except Exception as e:
        logger.warning(f"Template pushed but TTL update failed for {template_key}: {e}")
        return {
            "success": True,
            "template": template_key,
            "warning": f"Template pushed but TTL update failed: {e}",
        }

    return {"success": True, "template": template_key, "coder_template": coder_template_name}


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


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

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Build workspace images.

        Args:
            parameters: Dictionary containing:
                - templates: Optional list of template keys (None = all)
                - templates_dir: Path to templates directory
                - registry_host: Docker registry host
        """
        templates_dir = parameters.get("templates_dir", "/templates")
        registry_host = parameters.get("registry_host", "localhost:5000")
        requested = parameters.get("templates")

        template_keys = _resolve_templates(requested)
        if not template_keys:
            return WorkflowResult(
                status="failed",
                result=None,
                error="No valid templates specified",
                metadata={"workflow_type": "build_workspace_images"},
            )

        workflow.logger.info(f"Building images for templates: {template_keys}")

        results = []
        for key in template_keys:
            result = await workflow.execute_activity(
                build_workspace_image,
                args=[key, templates_dir, registry_host],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            results.append(result)

        failed = [r for r in results if not r.get("success")]
        if failed:
            return WorkflowResult(
                status="completed_with_errors",
                result={"builds": results},
                error=f"{len(failed)} build(s) failed",
                metadata={"workflow_type": "build_workspace_images"},
            )

        return WorkflowResult(
            status="completed",
            result={"builds": results},
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

    @workflow.run
    async def run(self, parameters: Dict[str, Any]) -> WorkflowResult:
        """
        Push Coder templates.

        Args:
            parameters: Dictionary containing:
                - templates: Optional list of template names (None = all)
                - build_images: Whether to build images first
                - templates_dir: Path to templates directory
                - registry_host: Docker registry host
                - coder_url: Coder server URL
                - coder_admin_email: Admin email
                - coder_admin_password: Admin password
                - backend_internal_url: Internal backend URL for Terraform
                - backend_external_url: External backend URL for Terraform
                - dev_forward_ports: Dev port forwarding config
                - ttl_ms: Default workspace TTL in ms
                - activity_bump_ms: Activity bump TTL in ms
        """
        templates_dir = parameters.get("templates_dir", "/templates")
        registry_host = parameters.get("registry_host", "localhost:5000")
        build_images = parameters.get("build_images", False)
        coder_url = parameters.get("coder_url", "http://coder:7080")
        coder_admin_email = parameters.get("coder_admin_email")
        coder_admin_password = parameters.get("coder_admin_password")
        backend_internal_url = parameters.get("backend_internal_url", "http://host.docker.internal:8000")
        backend_external_url = parameters.get("backend_external_url", "http://host.docker.internal:8000")
        dev_forward_ports = parameters.get("dev_forward_ports", "")
        ttl_ms = parameters.get("ttl_ms", 3600000)  # 1 hour default
        activity_bump_ms = parameters.get("activity_bump_ms", 3600000)

        if not coder_admin_email or not coder_admin_password:
            return WorkflowResult(
                status="failed",
                result=None,
                error="coder_admin_email and coder_admin_password are required",
                metadata={"workflow_type": "push_coder_templates"},
            )

        requested = parameters.get("templates")

        # Step 1: optionally build images
        if build_images:
            workflow.logger.info("Building images before pushing templates...")

            # Resolve template keys from requested coder template names
            # If user passes coder template names like "python-workspace", map back to keys
            build_keys = None
            if requested:
                build_keys = []
                for name in requested:
                    # Check if it's a coder template name, resolve to key
                    for key, info in TEMPLATE_REGISTRY.items():
                        if info["coder_template_name"] == name or key == name:
                            build_keys.append(key)
                            break

            build_result = await workflow.execute_activity(
                build_workspace_image,
                args=[
                    (build_keys or _get_all_template_keys())[0],
                    templates_dir,
                    registry_host,
                ],
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            # Build remaining
            for key in (build_keys or _get_all_template_keys())[1:]:
                await workflow.execute_activity(
                    build_workspace_image,
                    args=[key, templates_dir, registry_host],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5),
                        backoff_coefficient=2.0,
                        maximum_attempts=2,
                    ),
                )

        # Step 2: push templates
        # Resolve coder template names to push
        if requested:
            push_keys = []
            for name in requested:
                for key, info in TEMPLATE_REGISTRY.items():
                    if info["coder_template_name"] == name or key == name:
                        push_keys.append(key)
                        break
        else:
            push_keys = _get_all_template_keys()

        if not push_keys:
            return WorkflowResult(
                status="failed",
                result=None,
                error="No valid templates to push",
                metadata={"workflow_type": "push_coder_templates"},
            )

        workflow.logger.info(f"Pushing templates: {push_keys}")

        results = []
        for key in push_keys:
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
                ],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_attempts=2,
                ),
            )
            results.append(result)

        failed = [r for r in results if not r.get("success")]
        if failed:
            return WorkflowResult(
                status="completed_with_errors",
                result={"pushes": results},
                error=f"{len(failed)} push(es) failed",
                metadata={"workflow_type": "push_coder_templates"},
            )

        return WorkflowResult(
            status="completed",
            result={"pushes": results},
            metadata={"workflow_type": "push_coder_templates"},
        )
