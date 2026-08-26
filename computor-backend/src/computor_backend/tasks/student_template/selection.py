"""Deployment/content selection for a student-template release run."""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)


def select_deployments_for_release(
    db: Session,
    course_id: str,
    selected_course_content_ids: List[str],
    force_redeploy: bool,
):
    """Deployments a release run will move to 'deploying'.

    An explicit content selection wins; otherwise status-based (pending +
    failed, plus deployed under force_redeploy).
    """
    from ...model.course import CourseContent
    from ...model.deployment import CourseContentDeployment

    if selected_course_content_ids:
        return db.query(CourseContentDeployment).join(CourseContent).filter(
            and_(
                CourseContent.course_id == course_id,
                CourseContent.id.in_(selected_course_content_ids)
            )
        ).all()

    if force_redeploy:
        statuses_to_process = ["pending", "failed", "deployed"]
        logger.info(f"Force redeploy enabled - will reprocess deployed content for course {course_id}")
    else:
        statuses_to_process = ["pending", "failed"]
        logger.info(f"Updating deployments to 'deploying' status for course {course_id}")

    return db.query(CourseContentDeployment).join(
        CourseContent
    ).filter(
        and_(
            CourseContent.course_id == course_id,
            CourseContentDeployment.deployment_status.in_(statuses_to_process)
        )
    ).all()


def resolve_deployment_directory(deployment, *, persist: bool = False) -> Optional[str]:
    """Target directory for a deployment inside the template repo.

    Fallback chain: ``deployment_path`` → ``example_identifier`` →
    ``example_version.example.identifier``. With ``persist`` the resolved
    name is written back to ``deployment_path``.
    """
    directory_name = deployment.deployment_path
    if directory_name:
        return directory_name

    if deployment.example_identifier:
        directory_name = str(deployment.example_identifier)
        if persist:
            deployment.deployment_path = directory_name
            logger.info(f"Auto-set deployment_path from example_identifier: {directory_name}")
        return directory_name

    if deployment.example_version:
        try:
            example = deployment.example_version.example
            if example and example.identifier:
                directory_name = str(example.identifier)
                if persist:
                    deployment.deployment_path = directory_name
                    logger.info(f"Auto-set deployment_path from example.identifier: {directory_name}")
                return directory_name
        except AttributeError:
            # Lazy-loaded relationship missing under detached session — the
            # caller falls through to its no-directory error handling.
            pass
        except Exception as e:
            logger.warning(f"Could not get identifier from example_version: {e}")

    return None


def resolve_directory_owners(db: Session, course_id: str) -> Dict[str, str]:
    """Which course content owns each directory of the student template.

    Deployment paths are allocated collision-free at assign time
    (``business_logic.deployment_paths``), but courses assigned before that
    existed can still hold two contents pointing at one directory — that is
    computor-org/issues#150, and the release run is where it did its damage:
    the second content silently wrote over the first, and the student opened
    one assignment onto the other's files.

    Ownership goes to whoever released into the directory first, so a new
    assignment can never take a directory away from students already working
    in it. If nobody has released yet, the first by ltree path wins, which
    keeps the answer stable from run to run.
    """
    from ...model.course import CourseContent
    from ...model.deployment import CourseContentDeployment

    rows = db.query(CourseContent, CourseContentDeployment).join(
        CourseContentDeployment,
        CourseContentDeployment.course_content_id == CourseContent.id,
    ).filter(
        CourseContent.course_id == course_id,
        CourseContent.archived_at.is_(None),
        CourseContent.is_submittable.is_(True),
        CourseContentDeployment.deployment_status != "unassigned",
    ).order_by(CourseContent.path).all()

    owners: Dict[str, str] = {}
    claimed_by_release: Dict[str, Any] = {}
    for content, deployment in rows:
        directory = resolve_deployment_directory(deployment)
        if not directory:
            continue
        released_at = deployment.deployed_at
        if directory not in owners:
            owners[directory] = str(content.id)
            claimed_by_release[directory] = released_at
            continue
        # Someone already claims it. A completed release outranks a claim that
        # has never been released, and an earlier release outranks a later one.
        held = claimed_by_release.get(directory)
        if released_at is not None and (held is None or released_at < held):
            owners[directory] = str(content.id)
            claimed_by_release[directory] = released_at

    return owners


def select_contents_to_process(
    db: Session,
    course_id: str,
    selected_course_content_ids: List[str],
    force_redeploy: bool,
    existing_directories: Set[str],
) -> Tuple[list, int]:
    """Course contents this run must process, with repo-state verification.

    Scans ALL contents with deployments so that rows marked 'deployed' in
    the DB but missing from the cloned repository (state mismatch) are
    re-deployed. Mismatched deployments are flipped to 'deploying' here.

    Returns (contents_to_process, state_mismatch_count).
    """
    from ...model.course import CourseContent
    from ...model.deployment import CourseContentDeployment
    from ...model.example import ExampleVersion

    all_course_contents = db.query(CourseContent).options(
        joinedload(CourseContent.deployment)
            .joinedload(CourseContentDeployment.example_version)
            .joinedload(ExampleVersion.example)
    ).filter(
        CourseContent.course_id == course_id,
        CourseContent.archived_at.is_(None),
        # Only submittable content: a unit can be left holding a deployment
        # row by a past kind flip, and deploying a directory for a unit
        # corrupts the student template (computor-org/issues#320).
        CourseContent.is_submittable.is_(True),
        CourseContent.deployment.has()  # Has a deployment record
    ).order_by(CourseContent.path).all()

    logger.info(f"Found {len(all_course_contents)} course contents with deployments")

    course_contents = []
    state_mismatches = 0

    for content in all_course_contents:
        deployment_path = resolve_deployment_directory(content.deployment)
        exists_in_repo = deployment_path in existing_directories if deployment_path else False

        should_process = False
        reason = None

        # If specific contents were selected, only process those
        if selected_course_content_ids:
            if str(content.id) in selected_course_content_ids:
                should_process = True
                reason = "selected for deployment"
        else:
            if content.deployment.deployment_status in ["pending", "failed", "deploying"]:
                should_process = True
                reason = f"status={content.deployment.deployment_status}"
            elif force_redeploy:
                should_process = True
                reason = "force_redeploy=True"
            elif content.deployment.deployment_status == "deployed" and not exists_in_repo:
                # STATE MISMATCH: DB says deployed but missing from repository
                should_process = True
                reason = "STATE MISMATCH: marked deployed but missing from repository"
                state_mismatches += 1
                logger.warning(
                    f"🔄 STATE MISMATCH DETECTED: {content.path} ({deployment_path}) "
                    f"is marked as 'deployed' in database but MISSING from repository. "
                    f"Will re-deploy to fix inconsistency."
                )
                content.deployment.deployment_status = "deploying"
                content.deployment.deployment_message = "Re-deploying due to repository state mismatch"

        if should_process:
            course_contents.append(content)
            logger.info(f"  → Will process {content.path}: {reason}")

    if state_mismatches > 0:
        logger.warning(
            f"⚠️  Detected {state_mismatches} state mismatch(es) between database and repository. "
            f"These will be automatically fixed by re-deploying the missing content."
        )

    return course_contents, state_mismatches
