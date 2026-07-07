"""Deployment status transitions, history rows and event broadcasting.

All mutators only stage changes on the session — the activity owns the
commit so the deploying→deployed/failed ordering stays intact. Broadcast
AFTER a successful commit.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _history(deployment, action: str, workflow_id: Optional[str]):
    from ...model.deployment import DeploymentHistory

    return DeploymentHistory(
        deployment_id=deployment.id,
        action=action,
        example_version_id=deployment.example_version_id,
        workflow_id=workflow_id,
    )


def mark_deploying(db: Session, deployments, workflow_id: Optional[str]) -> List[Dict[str, Any]]:
    """Move deployments to 'deploying' (+history); returns broadcast events."""
    deploying_events = []
    for deployment in deployments:
        previous_status = deployment.deployment_status

        deployment.deployment_status = "deploying"
        deployment.last_attempt_at = datetime.now(timezone.utc)
        if workflow_id:
            deployment.workflow_id = workflow_id

        db.add(_history(deployment, "deploying", workflow_id))

        deploying_events.append({
            "deployment_id": str(deployment.id),
            "course_content_id": str(deployment.course_content_id),
            "previous_status": previous_status,
            "new_status": "deploying",
            "version_tag": deployment.version_tag,
            "example_identifier": str(deployment.example_identifier) if deployment.example_identifier else None,
        })
    return deploying_events


def mark_failed(db: Session, deployment, message: str, workflow_id: Optional[str]) -> None:
    """Move a deployment to 'failed' with a (truncated) message + history."""
    deployment.deployment_status = "failed"
    deployment.deployment_message = message[:500] if message else message
    db.add(_history(deployment, "failed", workflow_id))


def mark_deployed(
    db: Session,
    content,
    final_template_sha: Optional[str],
    workflow_id: Optional[str],
) -> Dict[str, Any]:
    """Move a successfully released content to 'deployed'; returns the event."""
    deployment = content.deployment
    deployment.deployment_status = "deployed"
    deployment.deployed_at = datetime.now(timezone.utc)
    deployment.deployment_message = None  # Clear any error messages

    # Store the student-template git commit SHA for audit trail — tracks
    # exactly which commit contains this deployment.
    if final_template_sha:
        deployment.version_identifier = final_template_sha

    # Ensure version_tag is populated from example_version (if not already
    # set); tracks which example version (from MinIO) was deployed.
    if not deployment.version_tag and deployment.example_version:
        try:
            deployment.version_tag = deployment.example_version.version_tag
            logger.info(f"Set version_tag={deployment.version_tag} for {content.path}")
        except Exception as e:
            logger.warning(f"Could not set version_tag for {content.path}: {e}")

    db.add(_history(deployment, "deployed", workflow_id))

    return {
        "course_content_id": str(content.id),
        "deployment_id": str(deployment.id),
        "previous_status": "deploying",
        "new_status": "deployed",
        "version_tag": deployment.version_tag,
        "example_identifier": str(deployment.example_identifier) if deployment.example_identifier else None,
        "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
    }


def failed_event(content) -> Dict[str, Any]:
    """Broadcast event for a deployment that ended up 'failed'."""
    deployment = content.deployment
    return {
        "course_content_id": str(content.id),
        "deployment_id": str(deployment.id),
        "previous_status": "deploying",
        "new_status": "failed",
        "deployment_message": deployment.deployment_message,
        "version_tag": deployment.version_tag,
        "example_identifier": str(deployment.example_identifier) if deployment.example_identifier else None,
    }


def collect_failed_events(course_contents, tracked_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Events for contents that failed during processing and aren't tracked yet."""
    events = []
    tracked_ids = {e["deployment_id"] for e in tracked_events}
    for content in course_contents:
        if content.deployment and content.deployment.deployment_status == "failed":
            if str(content.deployment.id) not in tracked_ids:
                events.append(failed_event(content))
    return events


def fail_all_deploying(db: Session, course_id: str, error_message: str, workflow_id: Optional[str]) -> List[Dict[str, Any]]:
    """Catch-all: mark every 'deploying' deployment of the course failed.

    Returns broadcast events for the affected deployments (broadcast after
    the caller commits).
    """
    from ...model.course import CourseContent
    from ...model.deployment import CourseContentDeployment

    failed_deployments = db.query(CourseContentDeployment).join(
        CourseContent
    ).filter(
        and_(
            CourseContent.course_id == course_id,
            CourseContentDeployment.deployment_status == "deploying"
        )
    ).all()

    events = []
    for deployment in failed_deployments:
        mark_failed(db, deployment, error_message, workflow_id)
        events.append({
            "course_content_id": str(deployment.course_content_id),
            "deployment_id": str(deployment.id),
            "previous_status": "deploying",
            "new_status": "failed",
            "deployment_message": error_message[:500] if error_message else error_message,
            "version_tag": deployment.version_tag,
            "example_identifier": str(deployment.example_identifier) if deployment.example_identifier else None,
        })
    return events


def broadcast_deployment_events(course_id: str, events: List[Dict[str, Any]], workflow_id: Optional[str]) -> None:
    """Publish deployment status changes. Call AFTER db.commit() succeeds."""
    from computor_backend.websocket.event_publisher import publish_deployment_status_changed

    for evt in events:
        publish_deployment_status_changed(
            course_id=str(course_id),
            course_content_id=evt["course_content_id"],
            deployment_id=evt["deployment_id"],
            previous_status=evt.get("previous_status"),
            new_status=evt["new_status"],
            version_tag=evt.get("version_tag"),
            example_identifier=evt.get("example_identifier"),
            deployment_message=evt.get("deployment_message"),
            deployed_at=evt.get("deployed_at"),
            workflow_id=workflow_id,
        )
