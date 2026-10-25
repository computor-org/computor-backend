#!/usr/bin/env python3
"""Synthetic baseline of the QA stack (computor-org/issues#529).

Runs inside the deployed API image (``qactl.sh`` mounts this file), so it uses
that ref's models for the few rows only the database can create, and the real
HTTP API for everything a person or the testing worker would do:

  baseline   persona users linked to their Keycloak ids, the admin role and an
             admin API token (printed as QA_ADMIN_API_TOKEN=... for qactl)
  content    the runnable examples package in /qa/examples (the python/
             directory of GitLab codeability/development/examples, with tests
             and reference solutions) uploaded through the examples API, the
             three course YAMLs of data-science-python (/qa/content) deployed
             under one course family, published in the catalog, assignments and
             student template released through the same endpoints the
             lecturer tools use
  templates  the vscode workspace image built and its Coder template pushed,
             and the courses' workspace settings; with a deployed VSIX the
             extension registry is held so workspaces keep that VSIX
  returning  the returning learner and a second learner: enrolled in
             Grundlagen, real submissions graded by the testing worker (the
             reference solution, one without docstring and an empty file), the
             next assignment left open, and a stopped workspace each

Every step is idempotent, so ``qactl.sh seed`` can run again on a seeded stack.
No real person's data is used: personas are @example.com accounts.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

import httpx
import yaml

API = os.environ.get("QA_API_URL", "http://uvicorn:8000").rstrip("/")
PERSONAS = json.loads(Path(os.environ.get("QA_PERSONAS_FILE", "/qa/personas.json")).read_text())
CREDENTIALS = Path("/qa/credentials.env")
CONTENT = Path("/qa/content")
EXAMPLES = Path("/qa/examples")

ORG_PATH = "itpcp"
ORG_TITLE = "ITPcp, TU Graz"
FAMILY_PATH = "data_science_python"
FAMILY_TITLE = "Data Science mit Python"
COURSE_FILES = ("python-beginner.yaml", "python-intermediate.yaml", "python-advanced.yaml")
GRUNDLAGEN_PATH = "python.beginner"
GRUNDLAGEN_FILE = "python-beginner.yaml"
COURSE_PATHS = ("python.beginner", "python.intermediate", "python.advanced")
WORKSPACE_TEMPLATE = "vscode-workspace"
# Learners with progress: what each submits per assignment, graded by a real
# test run. "correct" is the example's localTests/correctSolution, "nodoc" the
# same without its module docstring (plot_docstr checks it, so that attempt is
# partly right) and "empty" a file without code. The next assignment in order
# stays open (where a resume pointer should land).
LEARNER_SUBMISSIONS = {
    "returning": [
        ("week_1.math_constants", "correct"),
        ("week_1.basis1", "correct"),
        ("week_1.basis2", "empty"),
        ("week_1.plot_docstr", "nodoc"),
    ],
    "second": [
        ("week_1.math_constants", "correct"),
        ("week_1.basis1", "empty"),
    ],
}
RETURNING_OPEN = "week_1.simple_taylor"


def log(message: str) -> None:
    print(f"[qa-seed] {message}", flush=True)


def persona(key: str) -> dict:
    return next(p for p in PERSONAS if p["key"] == key)


def credential(name: str) -> str | None:
    if not CREDENTIALS.exists():
        return None
    for line in CREDENTIALS.read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    return None


# ------------------------------------------------------------------ DB ----

def ensure_user(session, data: dict):
    from computor_backend.model.auth import Account, User
    from computor_backend.model.role import UserRole

    account = (session.query(Account)
               .filter(Account.provider == "keycloak",
                       Account.provider_account_id == data["keycloak_id"])
               .one_or_none())
    user = None
    if account is not None:
        user = session.query(User).filter(User.id == account.user_id).one_or_none()
    if user is None:
        user = session.query(User).filter(User.email == data["email"]).one_or_none()
    if user is None:
        user = User(email=data["email"], given_name=data["given_name"],
                    family_name=data["family_name"],
                    properties={"qa_seed": True, "username": data["username"]})
        session.add(user)
        session.flush()
    if account is None:
        session.add(Account(provider="keycloak", type="oidc",
                            provider_account_id=data["keycloak_id"], user_id=user.id,
                            properties={"qa_seed": True, "username": data["username"]}))
    role = data.get("system_role")
    if role and session.query(UserRole).filter_by(user_id=user.id, role_id=role).one_or_none() is None:
        session.add(UserRole(user_id=user.id, role_id=role))
    session.flush()
    return user


def ensure_api_token(session, user, name: str) -> str | None:
    """A new token for ``user`` unless one named ``name`` exists (then None)."""
    from computor_backend.model.service import ApiToken
    from computor_backend.utils.api_token import generate_api_token

    existing = (session.query(ApiToken)
                .filter(ApiToken.user_id == user.id, ApiToken.name == name,
                        ApiToken.revoked_at.is_(None))
                .first())
    if existing is not None:
        return None
    token, prefix, token_hash = generate_api_token()
    session.add(ApiToken(name=name, description="QA stack automation (synthetic)",
                         user_id=user.id, token_hash=token_hash, token_prefix=prefix,
                         scopes=[]))
    session.flush()
    return token


def cmd_baseline() -> None:
    from computor_backend.database import get_db_session

    with get_db_session() as session:
        users = {p["key"]: ensure_user(session, p) for p in PERSONAS}
        # Agents' personas only: the personal tester's account gets no token.
        tokens = {key: ensure_api_token(session, users[key], f"qa-{key}-automation")
                  for key in ("admin", *LEARNER_SUBMISSIONS) if key in users}
        session.commit()
    for key, user in users.items():
        log(f"persona {key}: {persona(key)['email']} -> user {user.id}")
    # qactl.sh stores these lines in the 0600 credentials file.
    for key, token in tokens.items():
        if token:
            print(f"QA_{key.upper()}_API_TOKEN={token}")


# ----------------------------------------------------------------- API ----

class Api:
    def __init__(self, token: str):
        self.client = httpx.Client(base_url=API, timeout=120.0,
                                   headers={"X-API-Token": token})

    def request(self, method: str, path: str, ok=(200, 201), **kwargs):
        response = self.client.request(method, path, **kwargs)
        if response.status_code not in ok:
            raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:800]}")
        return response.json() if response.content else None

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def patch(self, path, **kw):
        return self.request("PATCH", path, **kw)

    def wait_task(self, task_id: str, label: str, timeout: float = 1800) -> dict:
        started = time.monotonic()
        while True:
            info = self.get(f"/tasks/{task_id}/status")
            status = info.get("status")
            if status == "finished":
                log(f"{label}: finished")
                return info
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"{label}: {status}: {info.get('error')}")
            if time.monotonic() - started > timeout:
                raise RuntimeError(f"{label}: still {status} after {timeout:.0f}s")
            time.sleep(5)


def admin_api() -> Api:
    token = credential("QA_ADMIN_API_TOKEN")
    if not token:
        raise SystemExit("no QA_ADMIN_API_TOKEN in the credentials file; run the baseline first")
    return Api(token)


def find_one(items, **match):
    for item in items:
        if all(item.get(k) == v for k, v in match.items()):
            return item
    return None


def submission_properties(directory: Path, meta: dict) -> dict | None:
    """``properties`` for an example whose public copy has none.

    Only for the fallback without the examples package: the public
    data-science-python mirror drops the instructor block of most meta.yaml
    files (submission file names, tests), and the student template refuses an
    example without it. The file names are the ``*.py`` names the German
    exercise text asks for, else ``<slug tail>.py``. Test runs of such an
    example error, because the mirror has no test.yaml.
    """
    props = dict(meta.get("properties") or {})
    if props.get("studentSubmissionFiles"):
        return None
    readme = directory / "content" / "index_de.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    names = list(dict.fromkeys(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*\.py)\b", text)))
    props["studentSubmissionFiles"] = names or [meta["slug"].rsplit(".", 1)[-1] + ".py"]
    props.setdefault("executionBackend", {"slug": "itpcp.exec.py"})
    return props


def example_files(directory: Path) -> dict[str, str]:
    files = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(directory).as_posix()
        data = path.read_bytes()
        try:
            files[rel] = data.decode("utf-8")
        except UnicodeDecodeError:
            files[rel] = base64.b64encode(data).decode("ascii")
    return files


def example_directories() -> tuple[list[Path], bool]:
    """The example directories to upload and whether they are runnable.

    computor.at's examples come from GitLab codeability/development/examples
    (``python/<slug>/`` with test.yaml, localTests and the full meta.yaml);
    ``qactl.sh`` extracts that package to /qa/examples. Without it, the public
    data-science-python mirror is the fallback, and its test runs error.
    """
    package = sorted(p.parent for p in EXAMPLES.glob("*/meta.yaml"))
    if package:
        return package, True
    return sorted(p.parent for p in (CONTENT / "examples").glob("*/*/meta.yaml")), False


def test_dependencies(meta: dict) -> list[str]:
    deps = meta.get("testDependencies") or (meta.get("properties") or {}).get("testDependencies") or []
    return [d.get("slug") if isinstance(d, dict) else str(d) for d in deps]


def upload_order(entries: list[tuple[Path, dict]]) -> list[tuple[Path, dict]]:
    """Dependencies before the examples that name them in testDependencies:
    the upload of an example whose dependency is missing is rejected."""
    by_slug = {meta.get("slug"): (directory, meta) for directory, meta in entries}
    ordered, done = [], set()

    def visit(slug, trail=()):
        if slug in done or slug not in by_slug:
            return
        if slug in trail:
            raise SystemExit(f"cyclic testDependencies: {' -> '.join(trail + (slug,))}")
        for dep in test_dependencies(by_slug[slug][1]):
            visit(dep, trail + (slug,))
        done.add(slug)
        ordered.append(by_slug[slug])

    for directory, meta in entries:
        visit(meta.get("slug"))
    return ordered


def cmd_content() -> None:
    if not (CONTENT / "courses").is_dir():
        raise SystemExit("no data-science-python checkout at /qa/content")
    api = admin_api()

    repos = api.get("/example-repositories")
    repo = find_one(repos, source_url="computor-storage") or (repos[0] if repos else None)
    if repo is None:
        raise SystemExit("no example repository; is data/deployments/example-repository.yaml staged?")

    directories, runnable = example_directories()
    if not runnable:
        log("no examples package in /qa/examples: falling back to the public mirror, "
            "whose test runs error")
    entries = [(d, yaml.safe_load((d / "meta.yaml").read_text(encoding="utf-8")) or {})
               for d in directories]
    uploaded = synthesized = 0
    for directory, meta in upload_order(entries):
        files = example_files(directory)
        if not runnable and (props := submission_properties(directory, meta)) is not None:
            meta["properties"] = props
            synthesized += 1
        # Re-running the step replaces the stored version instead of failing.
        meta["update_existing"] = True
        files["meta.yaml"] = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
        api.post("/examples/upload", json={"repository_id": repo["id"],
                                           "directory": directory.name,
                                           "files": files})
        uploaded += 1
    source = "examples package" if runnable else "public mirror"
    log(f"uploaded {uploaded} examples from the {source} to repository {repo['name']}"
        + (f" ({synthesized} with synthesized submission properties)" if synthesized else ""))

    org = find_one(api.get("/organizations", params={"path": ORG_PATH}), path=ORG_PATH)
    if org is None:
        org = api.post("/organizations", json={"path": ORG_PATH, "organization_type": "organization",
                                               "title": ORG_TITLE})
    family = find_one(api.get("/course-families", params={"path": FAMILY_PATH}), path=FAMILY_PATH)
    if family is None:
        family = api.post("/course-families", json={"path": FAMILY_PATH, "organization_id": org["id"],
                                                    "title": FAMILY_TITLE})

    for name in COURSE_FILES:
        text = (CONTENT / "courses" / name).read_text(encoding="utf-8")
        path = yaml.safe_load(text)["path"]
        existing = find_one(api.get("/courses", params={"path": path}), path=path)
        if existing is not None:
            # Releases are not re-applied onto a course with learners in it;
            # qactl.sh deploy --content-ref imports into a fresh baseline.
            log(f"{path}: already deployed, left as it is")
            ensure_lecturer(api, existing["id"], path)
            continue
        result = api.post(f"/course-families/{family['id']}/deploy-course",
                          json={"yaml": text, "validate_only": False})
        course_id = result.get("course_id")
        log(f"deployed {name}: course {course_id} applied={result.get('applied')}")
        if result.get("errors"):
            log(f"  deploy messages: {result.get('errors')}")
        api.patch(f"/courses/{course_id}", json={"public": True, "language_code": "de"})
        release_course(api, course_id, path)
        ensure_lecturer(api, course_id, path)


def ensure_lecturer(api: Api, course_id: str, path: str) -> None:
    """The lecturer persona teaches every QA course, so lecturer pages have data."""
    if not any(p["key"] == "lecturer" for p in PERSONAS):
        return
    email = persona("lecturer")["email"]
    user = find_one(api.get("/users", params={"email": email}), email=email)
    if user is None:
        raise SystemExit(f"no user {email}; run the baseline first")
    members = api.get("/course-members", params={"course_id": course_id, "user_id": user["id"]})
    if find_one(members, user_id=user["id"]) is not None:
        return
    api.post("/course-members", json={"user_id": user["id"], "course_id": course_id,
                                      "course_role_id": "_lecturer"})
    log(f"{path}: lecturer {email} added")


def release_course(api: Api, course_id: str, path: str) -> None:
    contents = api.get("/course-contents", params={"course_id": course_id, "limit": 1000})
    ids = [c["id"] for c in contents if c.get("has_deployment")]
    if not ids:
        log(f"{path}: nothing to release")
        return
    task = api.post(f"/system/courses/{course_id}/generate-assignments",
                    json={"course_content_ids": ids, "overwrite_strategy": "force_update",
                          "commit_message": "QA import"})
    api.wait_task(task["workflow_id"], f"{path}: assignments")
    task = api.post(f"/system/courses/{course_id}/generate-student-template",
                    json={"release": {"course_content_ids": ids}})
    api.wait_task(task.get("workflow_id") or task.get("task_id"), f"{path}: student template")


EXTENSION = "computor-org.computor"


def hold_extension_registry(api: Api) -> None:
    """With a VSIX baked into the image, yank every registry version.

    Workspaces otherwise replace the baked extension at start with the
    instance's approved (newest non-yanked) version whenever that one is newer
    (ops/coder/templates/README.md, "Extension updates"). An empty registry
    leaves the installed extension alone, and a yanked version stays yanked
    across backend restarts.
    """
    listing = api.get(f"/extensions/{EXTENSION}/versions",
                      params={"limit": 100}, ok=(200, 404)) or {}
    for item in listing.get("items", []):
        api.patch(f"/extensions/{EXTENSION}/versions/{item['version']}", json={"yanked": True})
        log(f"extension registry: {item['version']} yanked so the deployed VSIX stays")


def cmd_templates() -> None:
    """Build the vscode image and push its template.

    With a deployed VSIX, qactl.sh runs ``templates-build`` while the VSIX sits
    in the template directory, removes it (Coder refuses template archives over
    1 MiB) and then runs ``templates``, which pushes without rebuilding.
    """
    api = admin_api()
    vsix = bool(os.environ.get("QA_DEPLOYED_VSIX"))
    if vsix:
        hold_extension_registry(api)
    task = api.post("/coder/admin/templates/push",
                    json={"templates": ["vscode"], "build_images": not vsix})
    api.wait_task(task["workflow_id"], "vscode workspace template", timeout=3600)
    # The courses offer the managed VS Code workspace, as on computor.at.
    for path in COURSE_PATHS:
        course = find_one(api.get("/courses", params={"path": path}), path=path)
        if course is None:
            continue
        api.request("PUT", f"/courses/{course['id']}/workspace-settings",
                    json={"template_names": [WORKSPACE_TEMPLATE]})
        log(f"{path}: workspace template {WORKSPACE_TEMPLATE} enabled")


def submission_files(directory: Path, kind: str) -> dict[str, bytes]:
    """The submission files of one learner attempt at an example."""
    names = (yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8")) or {}) \
        .get("properties", {}).get("studentSubmissionFiles") or []
    if not names:
        raise RuntimeError(f"{directory.name}: no studentSubmissionFiles in meta.yaml")
    if kind == "empty":
        return {name: "# Noch nicht bearbeitet\n".encode() for name in names}
    source = directory / "localTests" / "correctSolution"
    files = {name: (source / name).read_bytes() for name in names}
    if kind == "nodoc":
        files = {name: re.sub(rb'\A\s*("""|\'\'\')(.*?)\1\s*', b"", data, flags=re.S)
                 for name, data in files.items()}
    return files


def course_examples(name: str) -> dict[str, str]:
    """Content path -> example identifier, from a course YAML of the mirror."""
    found = {}

    def walk(items, prefix):
        for item in items or []:
            path = f"{prefix}.{item['path']}" if prefix else item["path"]
            if item.get("example_identifier"):
                found[path] = item["example_identifier"]
            walk(item.get("contents"), path)

    walk(yaml.safe_load((CONTENT / "courses" / name).read_text(encoding="utf-8")).get("contents"), "")
    return found


def seed_learner(key: str, admin: Api, course: dict) -> None:
    token = credential(f"QA_{key.upper()}_API_TOKEN")
    if not token:
        raise SystemExit(f"no QA_{key.upper()}_API_TOKEN; run the baseline first")
    learner = Api(token)
    learner.request("POST", f"/user/courses/{course['id']}/enroll", ok=(200, 201))
    log(f"{key} learner enrolled in {course['title']}")

    contents = learner.get("/students/course-contents",
                           params={"course_id": course["id"], "limit": 1000})
    by_path = {c["path"]: c for c in contents}
    examples = {d.name: d for d in EXAMPLES.glob("*") if (d / "meta.yaml").is_file()}

    for path, kind in LEARNER_SUBMISSIONS[key]:
        content = by_path[path]
        if content.get("result"):
            continue
        group = content.get("submission_group") or {}
        if not group.get("id"):
            raise RuntimeError(f"{path}: no submission group for the learner: {content}")
        directory = content.get("directory") or path
        slug = course_examples(GRUNDLAGEN_FILE)[path]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            for name, data in submission_files(examples[slug], kind).items():
                zf.writestr(f"{directory}/{name}", data)
        upload = learner.post(
            "/submissions/artifacts",
            data={"submission_create": json.dumps({"submission_group_id": group["id"],
                                                   "version_identifier": f"qa-{key}-{path}",
                                                   "submit": True})},
            files={"file": ("submission.zip", archive.getvalue(), "application/zip")})
        # The same test run a learner starts with the beaker: the testing
        # worker grades the files against the example's test.yaml.
        run = learner.post("/tests", json={"artifact_id": upload["artifacts"][0]})
        deadline = time.monotonic() + 300
        while (result := admin.get(f"/results/{run['id']}")).get("status") in (
                "queued", "started", "deferred", "pending", "running", 4, 5, 7):
            if time.monotonic() > deadline:
                raise RuntimeError(f"{path}: test run {run['id']} did not finish")
            time.sleep(3)
        score = result.get("result")
        log(f"{key} {path}: submitted {kind}, test {result.get('status')}, "
            f"result {'-' if score is None else f'{score:.0%}'}")
    log(f"{key} {RETURNING_OPEN}: left open")
    ensure_stopped_workspace(learner, key)


def cmd_returning() -> None:
    if not any(EXAMPLES.glob("*/meta.yaml")):
        raise SystemExit("no examples package in /qa/examples: learners' submissions need "
                         "the reference solutions (qactl.sh deploy --examples FILE)")
    admin = admin_api()
    course = find_one(admin.get("/courses", params={"path": GRUNDLAGEN_PATH}), path=GRUNDLAGEN_PATH)
    if course is None:
        raise SystemExit("Grundlagen is not deployed; run the content step first")
    for key in LEARNER_SUBMISSIONS:
        if any(p["key"] == key for p in PERSONAS):
            seed_learner(key, admin, course)


def ensure_stopped_workspace(learner: Api, key: str, timeout: float = 900) -> None:
    """Provision the learner's workspace, let it start once, then stop it."""
    def current():
        items = learner.get("/coder/workspaces").get("workspaces") or []
        return items[0] if items else None

    ws = current()
    if ws is None:
        learner.post("/coder/workspaces/provision", json={"template": WORKSPACE_TEMPLATE})
        log(f"{key} learner: workspace provisioned")
    started = time.monotonic()
    while True:
        ws = current()
        state = (ws or {}).get("latest_build_transition"), (ws or {}).get("latest_build_status")
        # latest_build_status is Coder's workspace status (running, stopped, ...).
        if state[0] == "stop" and state[1] in ("stopped", "succeeded"):
            log(f"{key} learner: workspace {ws['name']} stopped")
            return
        if state[0] == "start" and state[1] in ("running", "succeeded"):
            learner.post(f"/coder/workspaces/{ws['owner_name']}/{ws['name']}/stop")
            log(f"{key} learner: stopping {ws['name']}")
        elif state[1] in ("failed", "canceled", "deleted"):
            raise RuntimeError(f"{key} learner workspace build {state}")
        if time.monotonic() - started > timeout:
            raise RuntimeError(f"{key} learner workspace still {state}")
        time.sleep(10)


def cmd_templates_build() -> None:
    api = admin_api()
    task = api.post("/coder/admin/images/build", json={"templates": ["vscode"]})
    api.wait_task(task["workflow_id"], "vscode workspace image", timeout=3600)


COMMANDS = {
    "baseline": cmd_baseline,
    "content": cmd_content,
    "templates-build": cmd_templates_build,
    "templates": cmd_templates,
    "returning": cmd_returning,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(f"usage: qa_seed.py {{{'|'.join(COMMANDS)}}}")
    COMMANDS[sys.argv[1]]()
