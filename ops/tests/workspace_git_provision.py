"""Provision a managed-Forgejo student repository the way the backend does.

Driver for test_workspace_git_clone.sh, not a test on its own. It uses the
backend's own Forgejo provider and git URL rendering against a throwaway
Forgejo, and writes what the extension would receive from
``POST /user/courses/{id}/provision-repository`` for a workspace caller —
workspace-facing clone URLs plus the student's clone credential — to a 0600
JSON file that the shell script hands to a git client inside the workspace
network. The credential is never printed.

Usage: python workspace_git_provision.py <forgejo-url> <root-url> <admin> <password> <out.json>
"""
import json
import os
import sys

from computor_backend.git_provider.forgejo import ForgejoProviderClient
from computor_backend.git_server import config as git_config

ORG = "ws-smoke-course"
TEMPLATE = "student-template"
STUDENT = "student42"


def main(base_url: str, root_url: str, admin: str, password: str, out_path: str) -> None:
    # The backend reaches Forgejo on its internal URL and surfaces its ROOT_URL
    # as the public host; a workspace caller gets neither, but computor-git.
    os.environ["GIT_SERVER_URL"] = base_url
    os.environ["FORGEJO_ROOT_URL"] = root_url
    os.environ.pop("GIT_SERVER_URL_PUBLIC", None)
    git_config.get_git_server_settings.cache_clear()

    service_token = ForgejoProviderClient(base_url, "").mint_admin_service_token(admin, password)
    assert service_token, "could not mint the admin service token"
    client = ForgejoProviderClient(base_url, service_token)

    client.create_course_org(ORG)
    template = client.ensure_template_repo(ORG, TEMPLATE)
    assert client.ensure_user(
        STUDENT, f"{STUDENT}@example.invalid", "Synthetic Student", admin, password
    ), "could not create the student's Forgejo account"

    repo = client.provision_student_fork(ORG, TEMPLATE, ORG, STUDENT, student_username=STUDENT)
    grants = repo.properties["forgejo"]
    assert grants["collaborator_added"], "write grant on the student repository failed"
    assert grants["template_read_granted"], "read grant on the course template failed"

    token = client.mint_user_clone_token(STUDENT, admin, password)
    assert token, "could not mint the student's clone token"

    git_config.set_git_audience(git_config.WORKSPACE_CLIENT_VALUE)
    student_url = git_config.to_public_git_url(repo.http_url)
    template_url = git_config.to_public_git_url(template["clone_url"])
    for url in (student_url, template_url):
        assert url.startswith(git_config.WORKSPACE_GIT_URL + "/"), f"not workspace-facing: {url}"

    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as out:
        json.dump(
            {
                "student_url": student_url,
                "template_url": template_url,
                "username": STUDENT,
                "token": token,
            },
            out,
        )
    print(f"provisioned {ORG}/{STUDENT}: {student_url} (template {template_url})")


if __name__ == "__main__":
    main(*sys.argv[1:6])
