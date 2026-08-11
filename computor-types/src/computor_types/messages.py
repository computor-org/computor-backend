from datetime import datetime
from typing import Optional, Literal, List, Protocol
from pydantic import BaseModel, ConfigDict, Field, computed_field

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery


class MessageTargetProtocol(Protocol):
    """
    Protocol for objects that have message target fields.

    Used for duck-typing SQLAlchemy models and Pydantic DTOs
    when determining WebSocket broadcast channels.
    """
    user_id: Optional[str]
    course_member_id: Optional[str]
    submission_group_id: Optional[str]
    course_content_id: Optional[str]
    course_group_id: Optional[str]
    course_id: Optional[str]
    course_family_id: Optional[str]
    organization_id: Optional[str]

MessageScope = Literal[
    "global",           # All users in the system can see
    "organization",     # Organization-level message
    "course_family",    # Course family-level message
    "course",           # Course-level message
    "course_content",   # Attached to specific course content
    "course_group",     # Attached to a course group
    "submission_group", # Attached to a submission group
    "course_member",    # Direct message to a course member
    "user",             # Direct message to a user (outside course context)
]


# Every target column on ``Message``, ordered most-specific first. The create
# path keeps exactly one of these set and forces the rest to NULL (the
# single-target invariant), and ``scope`` below is derived from whichever one
# survived — so this tuple and the ``scope`` priority chain must stay in the
# same order. It is the single source of truth for "what targets exist":
# message creation, the @mention audience gate and the WebSocket channel
# resolver all read it from here.
#
# ``course_group`` and ``course_content`` are siblings under a course, so
# their relative order is arbitrary — but it has to be *decided*, because
# a payload that sets both has to resolve the same way on the create path
# and in ``scope``. It previously did not.
MESSAGE_TARGET_FIELDS: tuple[str, ...] = (
    "user_id",
    "course_member_id",
    "submission_group_id",
    "course_group_id",
    "course_content_id",
    "course_id",
    "course_family_id",
    "organization_id",
)


MessageKind = Literal[
    "announcement",   # one-to-many broadcast: has a subject, no replies
    "conversation",   # back-and-forth chat: no subject, replies allowed
]


# The scopes that host a back-and-forth conversation. Everything else is
# announcement territory.
#
# This is the single source of truth for a split the system was already
# making in three places independently: replies were gated on it in the
# backend, and the VS Code extension re-derived it twice (once to hide the
# Reply button, once to hide the subject input). The rules that follow from
# it — subject required vs. forbidden, replies allowed vs. not, how a client
# should render the thread — now all read from here, and ``MessageGet.kind``
# ships it to clients so they never have to re-derive it at all.
#
# A student replying to a course-wide announcement would fan their reply out
# to every course member, which is the opposite of what an announcement is
# for; that is why the broadcast scopes are one-way.
CONVERSATIONAL_SCOPES: frozenset = frozenset({
    "user",
    "course_member",
    "submission_group",
})


def kind_for_scope(scope: MessageScope) -> MessageKind:
    """Whether ``scope`` is a conversation or an announcement."""
    return "conversation" if scope in CONVERSATIONAL_SCOPES else "announcement"


def normalize_title(title: Optional[str]) -> Optional[str]:
    """Collapse a blank subject to ``None``.

    A subject is either present or absent; ``""`` is neither. Clients that
    render no subject input still posted ``title: ""``, which filled the
    column with empty strings and made ``title IS NULL`` a lie.
    """
    if title is None:
        return None
    return title.strip() or None


def scope_for_targets(targets) -> MessageScope:
    """The scope of a message with the given target values.

    ``targets`` is anything supporting attribute *or* key access for the
    names in ``MESSAGE_TARGET_FIELDS`` — a Message row, a DTO, or the dict
    the create path builds. Returns ``"global"`` when no target is set.
    """
    for field in MESSAGE_TARGET_FIELDS:
        value = (
            targets.get(field)
            if isinstance(targets, dict)
            else getattr(targets, field, None)
        )
        if value is not None:
            # ``field`` is "<scope>_id"; the scope is the prefix.
            return field[:-3]  # type: ignore[return-value]
    return "global"


class MessageAuthor(BaseModel):
    """Author information for a message."""
    id: str = Field(..., description="User ID of the author")
    given_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's given name")
    family_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Author's family name")

    model_config = ConfigDict(from_attributes=True)


class MessageAuthorCourseMember(BaseModel):
    """Course member context for the message author (when message is in a course context)."""
    id: str = Field(..., description="Course member ID")
    course_role_id: str = Field(..., description="Role of the author in the course (e.g., '_student', '_tutor', '_lecturer')")
    course_id: str = Field(..., description="Course ID")

    model_config = ConfigDict(from_attributes=True)


class MessageMentionRef(BaseModel):
    """A user mentioned in a message.

    Resolved server-side from the ``@[Given Family](<user_id>)`` tokens in the
    message ``content``. The ``id`` (a ``user_id``) is authoritative; the name
    is refreshed from here on render so renames never go stale.
    """
    id: str = Field(..., description="User ID of the mentioned user")
    given_name: Optional[str] = Field(None, max_length=255, description="Mentioned user's given name")
    family_name: Optional[str] = Field(None, max_length=255, description="Mentioned user's family name")
    course_role_id: Optional[str] = Field(
        None, description="Mentioned user's course role within the message's course, if any"
    )

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    """A new message.

    ``title`` is the human subject line, and whether it is required is
    decided by the target's kind (see ``CONVERSATIONAL_SCOPES``):
    announcements must carry one, conversations must not. That rule is
    enforced server-side on create, because it is the only place that
    knows the resolved scope.
    """
    # author_id is always the current user; set in API
    parent_id: Optional[str] = None
    level: int = Field(
        default=0,
        deprecated=True,
        description=(
            "Ignored. Thread depth is derived server-side from parent_id "
            "(parent.level + 1, or 0 for a root)."
        ),
    )
    title: Optional[str] = Field(
        None,
        max_length=255,
        description=(
            "Subject line. Required for announcement scopes (global, "
            "organization, course_family, course, course_content, "
            "course_group); must be omitted for conversational scopes "
            "(submission_group, course_member, user)."
        ),
    )
    content: str

    # Targets (at least one should be provided, or none for global)
    # Hierarchy: organization > course_family > course > course_content/course_group > submission_group > course_member > user
    organization_id: Optional[str] = Field(None, description="Organization-level message")
    course_family_id: Optional[str] = Field(None, description="Course family-level message")
    course_id: Optional[str] = Field(None, description="Course-level message")
    course_content_id: Optional[str] = Field(None, description="Course content-level message")
    course_group_id: Optional[str] = Field(None, description="Course group-level message")
    submission_group_id: Optional[str] = Field(None, description="Submission group-level message")
    course_member_id: Optional[str] = Field(None, description="Direct message to a course member")
    user_id: Optional[str] = Field(None, description="Direct message to a user (outside course context)")

class MessageUpdate(BaseModel):
    """A partial edit. Only the fields actually sent are applied.

    An omitted ``title`` leaves the subject alone. A sent ``title`` is
    held to the same per-kind rule as on create, so an announcement
    cannot be stripped of its subject by an edit and a conversation
    cannot acquire one.
    """
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None

class MessageGet(BaseEntityGet):
    id: str
    title: Optional[str] = None
    content: str
    level: int
    parent_id: Optional[str] = None
    author_id: str
    author: Optional[MessageAuthor] = Field(None, description="Author details (user info)")
    author_course_member: Optional[MessageAuthorCourseMember] = Field(
        None, description="Author's course member context (only for course-scoped messages)"
    )
    mentions: List[MessageMentionRef] = Field(
        default_factory=list, description="Users mentioned in this message"
    )
    is_read: bool = False
    is_author: bool = Field(False, description="True if the requesting user is the message author")
    is_deleted: bool = Field(False, description="True if the message has been soft-deleted")
    deleted_by: Optional[str] = Field(None, description="Who deleted the message (author/moderator/admin)")

    # Target fields (determines scope)
    organization_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_member_id: Optional[str] = None
    user_id: Optional[str] = None

    @computed_field
    @property
    def scope(self) -> MessageScope:
        """Message scope, derived from whichever target field is set."""
        return scope_for_targets(self)

    @computed_field
    @property
    def kind(self) -> MessageKind:
        """Conversation or announcement — see ``CONVERSATIONAL_SCOPES``.

        Shipped alongside ``scope`` so clients can branch on it (subject,
        replies, how to render the list) without re-deriving the split and
        drifting from the server.
        """
        return kind_for_scope(self.scope)

    model_config = ConfigDict(from_attributes=True)

class MessageList(BaseEntityList):
    id: str
    title: Optional[str] = None
    content: str
    level: int
    parent_id: Optional[str] = None
    author_id: str
    author: Optional[MessageAuthor] = Field(None, description="Author details (user info)")
    author_course_member: Optional[MessageAuthorCourseMember] = Field(
        None, description="Author's course member context (only for course-scoped messages)"
    )
    mentions: List[MessageMentionRef] = Field(
        default_factory=list, description="Users mentioned in this message"
    )
    is_read: bool = False
    is_author: bool = Field(False, description="True if the requesting user is the message author")
    is_deleted: bool = Field(False, description="True if the message has been soft-deleted")
    deleted_by: Optional[str] = Field(None, description="Who deleted the message (author/moderator/admin)")

    # Target fields (determines scope)
    organization_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_member_id: Optional[str] = None
    user_id: Optional[str] = None

    @computed_field
    @property
    def scope(self) -> MessageScope:
        """Message scope, derived from whichever target field is set."""
        return scope_for_targets(self)

    @computed_field
    @property
    def kind(self) -> MessageKind:
        """Conversation or announcement — see ``CONVERSATIONAL_SCOPES``.

        Shipped alongside ``scope`` so clients can branch on it (subject,
        replies, how to render the list) without re-deriving the split and
        drifting from the server.
        """
        return kind_for_scope(self.scope)

    model_config = ConfigDict(from_attributes=True)

class MessageQuery(ListQuery):
    """Query parameters for ``GET /messages``.

    Target-id filters walk FK relations *down* to children: filtering by
    ``course_id=X`` returns every message reachable through course X
    (messages with ``course_id=X`` directly, plus messages on any
    course_content / course_group / submission_group / course_member of
    that course). Pair with ``scope=`` to restrict to a specific target
    type, e.g. ``course_id=X & scope=submission_group`` for "every
    submission-group message in course X".

    Walk targets:

    * ``organization_id`` → course_family, course, course_content,
      course_group, submission_group, course_member of that organization.
    * ``course_family_id`` → course, course_content, course_group,
      submission_group, course_member of that course_family.
    * ``course_id`` → course_content, course_group, submission_group,
      course_member of that course.
    * ``course_content_id`` → submission_group of that course_content.
    * ``course_group_id`` → course_member of that course_group.
    * ``submission_group_id`` → course_member of that submission_group
      (via SubmissionGroupMember).

    Strict targets (no children):

    * ``course_member_id`` — direct messages to a course_member.
    * ``user_id`` — direct messages to a user.

    Permission filtering (``MessagePermissionHandler``) runs in addition
    to these filters, so the walked set is always narrowed to what the
    caller is actually allowed to read.
    """

    id: Optional[str] = None
    parent_id: Optional[str] = None
    author_id: Optional[str] = None

    # Target filters — parent ids walk down to children, leaf ids
    # (``course_member_id``, ``user_id``) match strictly. See class
    # docstring for the full hierarchy.
    organization_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_member_id: Optional[str] = None
    user_id: Optional[str] = None

    # Filter by message scope (e.g., "global", "organization", "course", "course_content", "submission_group")
    scope: Optional[MessageScope] = None

    # Filter by kind — every conversational scope at once, or every
    # announcement scope at once. Coarser than ``scope`` and the natural
    # axis for an inbox that renders the two differently.
    kind: Optional[MessageKind] = None

    # Datetime boundary filters (based on created_at)
    created_after: Optional[datetime] = Field(
        None, description="Filter messages created at or after this datetime (inclusive)"
    )
    created_before: Optional[datetime] = Field(
        None, description="Filter messages created at or before this datetime (inclusive)"
    )

    # Unread filter (from current API user's perspective)
    unread: Optional[bool] = Field(
        None, description="Filter by read status: True = unread only, False = read only, None = all"
    )

    # Mention filters (resolved against the message_mention relation, then
    # narrowed by MessagePermissionHandler like every other filter)
    mentioned_user_id: Optional[str] = Field(
        None, description="Only messages that mention this user_id"
    )
    mentions_me: Optional[bool] = Field(
        None, description="Only messages that mention the current API user"
    )

    # Tag filtering (tags in title: #<tag> where tag is any non-whitespace string)
    tags: Optional[List[str]] = Field(
        None, description="Filter by tags in title (e.g., ['ai', 'ai-help', 'review']). Without # prefix."
    )
    tags_match_all: Optional[bool] = Field(
        True, description="True = must match ALL tags (AND), False = match ANY tag (OR)"
    )
    tag_scope: Optional[str] = Field(
        None, description="Filter by tag prefix (e.g., 'ai' matches #ai, #ai-help, #ai-response, etc.)"
    )

    # Soft-deleted messages are hidden by default, matching the thread
    # endpoint. Opt in only for audit/moderation views.
    include_deleted: Optional[bool] = Field(
        False, description="Include soft-deleted (archived) messages in the result"
    )


class MentionableQuery(BaseModel):
    """Query for ``GET /messages/mentionable-users``.

    Identifies the message scope whose audience (the users who may be
    @mentioned) to list. Provide the same target you would post to, or
    ``parent_id`` to inherit a thread's scope; ``search`` filters candidates by
    name for large audiences.
    """
    parent_id: Optional[str] = Field(None, description="Inherit scope from this parent/thread message")
    organization_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    submission_group_id: Optional[str] = None
    course_member_id: Optional[str] = None
    user_id: Optional[str] = None
    search: Optional[str] = Field(None, description="Filter candidates by given/family name")
    limit: int = Field(50, le=200, description="Maximum number of candidates to return")


class MessageReadBulk(BaseModel):
    """Body for ``POST /messages/reads/bulk`` — mark many messages read at once.

    Ids the caller cannot see are skipped rather than rejecting the batch:
    a read sweep is best-effort, and a client learns nothing useful from
    an id it was never shown in the first place.
    """
    message_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Message ids to mark as read for the current user",
    )


class MessageReadBulkResult(BaseModel):
    """What a bulk mark-read actually changed."""
    marked: int = Field(
        0, description="How many messages were newly marked read"
    )
    requested: int = Field(
        0, description="How many ids were submitted (after de-duplication)"
    )


class MessageThread(BaseModel):
    """Full conversation thread for a message.

    Returns all messages sharing the same root, ordered by created_at.
    Used by agents to get full conversation context for follow-up detection.
    """
    root_message_id: str = Field(..., description="ID of the root message in the thread")
    messages: list[MessageList] = Field(
        default_factory=list,
        description="All messages in the thread, ordered by created_at ascending"
    )
    total: int = Field(0, description="Total number of messages in the thread")

    model_config = ConfigDict(from_attributes=True)


class MessageInterface(EntityInterface):
    create = MessageCreate
    get = MessageGet
    list = MessageList
    update = MessageUpdate
    query = MessageQuery
