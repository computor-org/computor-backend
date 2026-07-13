"""Message business logic.

Split from a single 1,336-line module into cohesive submodules; this package
re-exports the full public surface so existing ``from
computor_backend.business_logic.messages import X`` call sites are unchanged.

Layering (import DAG, no cycles):
    audience, permissions, cache  -> leaves
    mentions      -> audience
    read_status   -> mentions, cache
    core          -> permissions, mentions, read_status
    lifecycle     -> (standalone)
"""
from .core import (
    MESSAGE_TARGET_FIELDS,
    CONVERSATIONAL_TARGET_FIELDS,
    create_message_with_author,
    list_messages_with_filters,
    get_message_thread,
)
from .permissions import (
    _principal_has_course_role,
    _check_global_write_permission,
    _check_user_message_write_permission,
    _check_organization_write_permission,
    _check_course_family_write_permission,
    _check_course_group_write_permission,
    _check_submission_group_write_permission,
    _check_course_content_write_permission,
    _check_course_write_permission,
)
from .audience import get_message_recipient_user_ids, _elevated_user_ids
from .mentions import (
    MENTION_PATTERN,
    extract_mention_user_ids,
    message_audience_user_ids,
    validate_message_mentions,
    sync_message_mentions,
    list_mentionable_users,
)
from .cache import (
    invalidate_dashboard_views_for_message,
    invalidate_tutor_lecturer_views_for_message,
    invalidate_course_dashboards,
)
from .read_status import (
    mark_author_as_reader,
    get_message_with_read_status,
    list_messages_with_read_status,
    mark_message_as_read,
    mark_message_as_unread,
)
from .lifecycle import (
    soft_delete_message,
    update_message_with_audit,
    create_message_audit,
    get_message_audit_history,
)

__all__ = [
    "MESSAGE_TARGET_FIELDS",
    "CONVERSATIONAL_TARGET_FIELDS",
    "create_message_with_author",
    "list_messages_with_filters",
    "get_message_thread",
    "_principal_has_course_role",
    "_check_global_write_permission",
    "_check_user_message_write_permission",
    "_check_organization_write_permission",
    "_check_course_family_write_permission",
    "_check_course_group_write_permission",
    "_check_submission_group_write_permission",
    "_check_course_content_write_permission",
    "_check_course_write_permission",
    "get_message_recipient_user_ids",
    "_elevated_user_ids",
    "MENTION_PATTERN",
    "extract_mention_user_ids",
    "message_audience_user_ids",
    "validate_message_mentions",
    "sync_message_mentions",
    "list_mentionable_users",
    "invalidate_dashboard_views_for_message",
    "invalidate_tutor_lecturer_views_for_message",
    "invalidate_course_dashboards",
    "mark_author_as_reader",
    "get_message_with_read_status",
    "list_messages_with_read_status",
    "mark_message_as_read",
    "mark_message_as_unread",
    "soft_delete_message",
    "update_message_with_audit",
    "create_message_audit",
    "get_message_audit_history",
]
