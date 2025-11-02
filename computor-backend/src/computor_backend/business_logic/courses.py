"""
Business logic for course management.

NOTE: This file previously contained CourseExecutionBackend management functions.
These have been removed as part of the refactoring to ServiceType architecture.

Legacy functions removed:
- update_course_execution_backend() - Use ServiceType configuration instead
- delete_course_execution_backend() - No longer needed (scope-based auth)

See docs/SERVICE_TYPE_LTREE_DESIGN.md for the new architecture.
"""
import logging

logger = logging.getLogger(__name__)

# This file is deprecated and will be removed in a future version
# All course execution backend logic has been replaced by the ServiceType system
