"""Live deploy test: the GitLab builder creates ONLY the course group.

Drives ``gitlab_builder._create_organization`` / ``_create_course_family`` /
``_create_course`` against a real GitLab + a real Postgres and asserts the
course-group-only model: org and family create NO GitLab group; the course group
is created directly under the organization's hand-made ``parent`` group. It
creates throwaway DB rows + a GitLab group and cleans both up afterwards.

Skipped unless ``DEPLOY_IT_DB_URL`` (a SQLAlchemy URL) and ``TOKEN_SECRET`` are
set, in addition to the ``GITLAB_IT_*`` config (see ``fixtures/gitlab.py``).
"""
import os
import time

import pytest

pytestmark = pytest.mark.deployment


@pytest.fixture(scope="module")
def db_session():
    url = os.environ.get("DEPLOY_IT_DB_URL")
    if not url or not os.environ.get("TOKEN_SECRET"):
        pytest.skip("Set DEPLOY_IT_DB_URL + TOKEN_SECRET (and GITLAB_IT_*) to run the deploy test.")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(url)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_gitlab_deploy_creates_only_course_group(db_session, gitlab_cfg):
    from sqlalchemy import text

    from computor_backend.generator.gitlab_builder import GitLabBuilder
    from computor_types.deployment_config import (
        CourseConfig,
        CourseFamilyConfig,
        OrganizationConfig,
    )
    from computor_types.gitlab import GitLabConfig

    url, token, parent = gitlab_cfg["url"], gitlab_cfg["token"], gitlab_cfg["parent_group_id"]
    sfx = str(int(time.time()))[-6:]
    builder = GitLabBuilder(db_session, url, token)
    made = {"org": None, "fam": None, "crs": None, "glgrp": None}
    try:
        r = builder._create_organization(
            OrganizationConfig(
                name="IT Org", path=f"itdep{sfx}", description="",
                gitlab=GitLabConfig(url=url, token=token, parent=parent, path=f"itdep{sfx}"),
            ),
            None,
        )
        assert r["success"], r
        made["org"] = r["organization"]
        assert r.get("gitlab_group") is None, "org must create NO GitLab group"
        assert (made["org"].properties or {}).get("gitlab", {}).get("parent") == parent

        r = builder._create_course_family(
            CourseFamilyConfig(name="F", path=f"f{sfx}", description=""), made["org"], None
        )
        assert r["success"], r
        made["fam"] = r["course_family"]
        assert r.get("gitlab_group") is None, "family must create NO GitLab group"

        r = builder._create_course(
            CourseConfig(name="C", path=f"c{sfx}", description=""), made["org"], made["fam"], None
        )
        assert r["success"], r
        made["crs"] = r["course"]
        grp = r.get("gitlab_group")
        assert grp is not None, "course MUST create a GitLab group"
        made["glgrp"] = grp.id
        assert int(grp.parent_id) == parent, "course group must sit under the org's hand-made parent"
        db_session.commit()
    finally:
        try:
            if made["glgrp"]:
                import gitlab

                gitlab.Gitlab(url, private_token=token).groups.delete(made["glgrp"])
        except Exception:
            pass
        db_session.rollback()
        for key, tbl in (("crs", "course"), ("fam", "course_family"), ("org", "organization")):
            if made[key] is not None:
                try:
                    db_session.execute(text(f"delete from {tbl} where id = :id"), {"id": str(made[key].id)})
                except Exception:
                    db_session.rollback()
        db_session.commit()
