"""Helpers for the student-template release activity.

``generate_student_template_activity_v2`` orchestrates a release; the
domain steps live here, Temporal-free and individually testable:

- selection:    which deployments/contents a run processes (incl. the
                repo-state-mismatch scan)
- status:       deploying/deployed/failed transitions + history rows and
                the post-commit websocket broadcast
- readme:       top-level README generation
- service_link: legacy testing-service fallback linking
- reference:    staff-only reference-repo mirroring
"""

from .selection import (  # noqa: F401
    resolve_deployment_directory,
    select_contents_to_process,
    select_deployments_for_release,
)
from .status import (  # noqa: F401
    broadcast_deployment_events,
    collect_failed_events,
    fail_all_deploying,
    mark_deployed,
    mark_deploying,
    mark_failed,
)
from .readme import generate_main_readme  # noqa: F401
from .service_link import link_testing_service  # noqa: F401
from .reference import (  # noqa: F401
    REFERENCE_INCLUDE_FULL_EXAMPLE,
    process_example_for_reference_v2,
    push_reference_repo,
)
