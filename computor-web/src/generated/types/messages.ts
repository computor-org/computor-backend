/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Messages

 */



import type { MessageAuthor, MessageAuthorCourseMember } from './auth';



/**
 * A user mentioned in a message.
 * 
 * Resolved server-side from the ``@[Given Family](<user_id>)`` tokens in the
 * message ``content``. The ``id`` (a ``user_id``) is authoritative; the name
 * is refreshed from here on render so renames never go stale.
 */
export interface MessageMentionRef {
  /** User ID of the mentioned user */
  id: string;
  /** Mentioned user's given name */
  given_name?: string | null;
  /** Mentioned user's family name */
  family_name?: string | null;
  /** Mentioned user's course role within the message's course, if any */
  course_role_id?: string | null;
}

/**
 * A member of the submission group a message is attached to.
 */
export interface MessageContextMember {
  /** Course member ID of the group member */
  course_member_id: string;
  /** User ID of the group member */
  user_id?: string | null;
  /** Member's given name */
  given_name?: string | null;
  /** Member's family name */
  family_name?: string | null;
}

/**
 * Human-readable placement of a message, resolved server-side.
 * 
 * A message row carries exactly one target id (the single-target
 * invariant), which is meaningless to a human — clients used to render
 * "Submission Group e86522aa". This object names the surroundings: the
 * course, the course content (for submission-group messages resolved via
 * the group's ``course_content_id``), the course group, and the
 * submission group's members. Populated on list/get for every message
 * that has a resolvable course; ``None`` for global / organization /
 * course_family / user-scoped messages.
 */
export interface MessageContext {
  /** Resolved course ID */
  course_id?: string | null;
  /** Resolved course title */
  course_title?: string | null;
  /** Course content the message belongs to (direct or via submission group) */
  course_content_id?: string | null;
  /** Course content title */
  course_content_title?: string | null;
  /** Course content ltree path */
  course_content_path?: string | null;
  /** Course group the message targets */
  course_group_id?: string | null;
  /** Course group title */
  course_group_title?: string | null;
  /** Submission group team name, or the first member's full name */
  submission_group_display_name?: string | null;
  /** Members of the message's submission group */
  submission_group_members?: MessageContextMember[];
}

/**
 * A new message.
 * 
 * ``title`` is the human subject line, and whether it is required is
 * decided by the target's kind (see ``CONVERSATIONAL_SCOPES``):
 * announcements must carry one, conversations must not. That rule is
 * enforced server-side on create, because it is the only place that
 * knows the resolved scope.
 */
export interface MessageCreate {
  parent_id?: string | null;
  /** Ignored. Thread depth is derived server-side from parent_id (parent.level + 1, or 0 for a root). */
  level?: number;
  /** Subject line. Required for announcement scopes (global, organization, course_family, course, course_content, course_group); must be omitted for conversational scopes (submission_group, course_member, user). */
  title?: string | null;
  content: string;
  /** Organization-level message */
  organization_id?: string | null;
  /** Course family-level message */
  course_family_id?: string | null;
  /** Course-level message */
  course_id?: string | null;
  /** Course content-level message */
  course_content_id?: string | null;
  /** Course group-level message */
  course_group_id?: string | null;
  /** Submission group-level message */
  submission_group_id?: string | null;
  /** Direct message to a course member */
  course_member_id?: string | null;
  /** Direct message to a user (outside course context) */
  user_id?: string | null;
}

/**
 * A partial edit. Only the fields actually sent are applied.
 * 
 * An omitted ``title`` leaves the subject alone. A sent ``title`` is
 * held to the same per-kind rule as on create, so an announcement
 * cannot be stripped of its subject by an edit and a conversation
 * cannot acquire one.
 */
export interface MessageUpdate {
  title?: string | null;
  content?: string | null;
}

export interface MessageGet {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  created_by?: string | null;
  updated_by?: string | null;
  id: string;
  title?: string | null;
  content: string;
  level: number;
  parent_id?: string | null;
  author_id: string;
  /** Author details (user info) */
  author?: MessageAuthor | null;
  /** Author's course member context (only for course-scoped messages) */
  author_course_member?: MessageAuthorCourseMember | null;
  /** Users mentioned in this message */
  mentions?: MessageMentionRef[];
  is_read?: boolean;
  /** True if the requesting user is the message author */
  is_author?: boolean;
  /** True if the message has been soft-deleted */
  is_deleted?: boolean;
  /** Who deleted the message (author/moderator/admin) */
  deleted_by?: string | null;
  /** Resolved human-readable placement (course/content/group names) */
  context?: MessageContext | null;
  organization_id?: string | null;
  course_family_id?: string | null;
  course_id?: string | null;
  course_content_id?: string | null;
  course_group_id?: string | null;
  submission_group_id?: string | null;
  course_member_id?: string | null;
  user_id?: string | null;
  /** Message scope, derived from whichever target field is set. */
  scope: "global" | "organization" | "course_family" | "course" | "course_content" | "course_group" | "submission_group" | "course_member" | "user";
  /** Conversation or announcement — see ``CONVERSATIONAL_SCOPES``.

Shipped alongside ``scope`` so clients can branch on it (subject,
replies, how to render the list) without re-deriving the split and
drifting from the server. */
  kind: "announcement" | "conversation";
}

export interface MessageList {
  /** Creation timestamp */
  created_at?: string | null;
  /** Update timestamp */
  updated_at?: string | null;
  id: string;
  title?: string | null;
  content: string;
  level: number;
  parent_id?: string | null;
  author_id: string;
  /** Author details (user info) */
  author?: MessageAuthor | null;
  /** Author's course member context (only for course-scoped messages) */
  author_course_member?: MessageAuthorCourseMember | null;
  /** Users mentioned in this message */
  mentions?: MessageMentionRef[];
  is_read?: boolean;
  /** True if the requesting user is the message author */
  is_author?: boolean;
  /** True if the message has been soft-deleted */
  is_deleted?: boolean;
  /** Who deleted the message (author/moderator/admin) */
  deleted_by?: string | null;
  /** Resolved human-readable placement (course/content/group names) */
  context?: MessageContext | null;
  organization_id?: string | null;
  course_family_id?: string | null;
  course_id?: string | null;
  course_content_id?: string | null;
  course_group_id?: string | null;
  submission_group_id?: string | null;
  course_member_id?: string | null;
  user_id?: string | null;
  /** Message scope, derived from whichever target field is set. */
  scope: "global" | "organization" | "course_family" | "course" | "course_content" | "course_group" | "submission_group" | "course_member" | "user";
  /** Conversation or announcement — see ``CONVERSATIONAL_SCOPES``.

Shipped alongside ``scope`` so clients can branch on it (subject,
replies, how to render the list) without re-deriving the split and
drifting from the server. */
  kind: "announcement" | "conversation";
}

/**
 * Query parameters for ``GET /messages``.
 * 
 * Target-id filters walk FK relations *down* to children: filtering by
 * ``course_id=X`` returns every message reachable through course X
 * (messages with ``course_id=X`` directly, plus messages on any
 * course_content / course_group / submission_group / course_member of
 * that course). Pair with ``scope=`` to restrict to a specific target
 * type, e.g. ``course_id=X & scope=submission_group`` for "every
 * submission-group message in course X".
 * 
 * Walk targets:
 * 
 * * ``organization_id`` → course_family, course, course_content,
 * course_group, submission_group, course_member of that organization.
 * * ``course_family_id`` → course, course_content, course_group,
 * submission_group, course_member of that course_family.
 * * ``course_id`` → course_content, course_group, submission_group,
 * course_member of that course.
 * * ``course_content_id`` → submission_group of that course_content.
 * * ``course_group_id`` → course_member of that course_group.
 * * ``submission_group_id`` → course_member of that submission_group
 * (via SubmissionGroupMember).
 * 
 * Strict targets (no children):
 * 
 * * ``course_member_id`` — direct messages to a course_member.
 * * ``user_id`` — direct messages to a user.
 * 
 * Permission filtering (``MessagePermissionHandler``) runs in addition
 * to these filters, so the walked set is always narrowed to what the
 * caller is actually allowed to read.
 */
export interface MessageQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  parent_id?: string | null;
  author_id?: string | null;
  organization_id?: string | null;
  course_family_id?: string | null;
  course_id?: string | null;
  course_content_id?: string | null;
  course_group_id?: string | null;
  submission_group_id?: string | null;
  course_member_id?: string | null;
  user_id?: string | null;
  scope?: "global" | "organization" | "course_family" | "course" | "course_content" | "course_group" | "submission_group" | "course_member" | "user" | null;
  kind?: "announcement" | "conversation" | null;
  /** Filter messages created at or after this datetime (inclusive) */
  created_after?: string | null;
  /** Filter messages created at or before this datetime (inclusive) */
  created_before?: string | null;
  /** Filter by read status: True = unread only, False = read only, None = all */
  unread?: boolean | null;
  /** Only messages that mention this user_id */
  mentioned_user_id?: string | null;
  /** Only messages that mention the current API user */
  mentions_me?: boolean | null;
  /** Filter by tags in title (e.g., ['ai', 'ai-help', 'review']). Without # prefix. */
  tags?: string[] | null;
  /** True = must match ALL tags (AND), False = match ANY tag (OR) */
  tags_match_all?: boolean | null;
  /** Filter by tag prefix (e.g., 'ai' matches #ai, #ai-help, #ai-response, etc.) */
  tag_scope?: string | null;
  /** Include soft-deleted (archived) messages in the result */
  include_deleted?: boolean | null;
}

/**
 * Query for ``GET /messages/mentionable-users``.
 * 
 * Identifies the message scope whose audience (the users who may be
 * @mentioned) to list. Provide the same target you would post to, or
 * ``parent_id`` to inherit a thread's scope; ``search`` filters candidates by
 * name for large audiences.
 */
export interface MentionableQuery {
  /** Inherit scope from this parent/thread message */
  parent_id?: string | null;
  organization_id?: string | null;
  course_family_id?: string | null;
  course_id?: string | null;
  course_content_id?: string | null;
  course_group_id?: string | null;
  submission_group_id?: string | null;
  course_member_id?: string | null;
  user_id?: string | null;
  /** Filter candidates by given/family name */
  search?: string | null;
  /** Maximum number of candidates to return */
  limit?: number;
}

/**
 * Body for ``POST /messages/reads/bulk`` — mark many messages read at once.
 * 
 * Ids the caller cannot see are skipped rather than rejecting the batch:
 * a read sweep is best-effort, and a client learns nothing useful from
 * an id it was never shown in the first place.
 */
export interface MessageReadBulk {
  /** Message ids to mark as read for the current user */
  message_ids: string[];
}

/**
 * What a bulk mark-read actually changed.
 */
export interface MessageReadBulkResult {
  /** How many messages were newly marked read */
  marked?: number;
  /** How many ids were submitted (after de-duplication) */
  requested?: number;
}

/**
 * Message totals for one ``(scope, course)`` cell.
 * 
 * ``course_id`` is the *resolved* course — for a submission-group or
 * course-content message that is the course reached through the target,
 * not a column on the message row itself. ``None`` for the scopes that
 * have no single course (global, organization, course_family, user).
 */
export interface MessageScopeCounts {
  scope: "global" | "organization" | "course_family" | "course" | "course_content" | "course_group" | "submission_group" | "course_member" | "user";
  /** Resolved course, if the scope has one */
  course_id?: string | null;
  /** Visible messages in this cell */
  total?: number;
  /** Visible messages not yet read by the caller (own posts excluded) */
  unread?: number;
}

/**
 * Response of ``GET /messages/counts``.
 * 
 * One aggregate query over the caller's full read visibility — the same
 * permission filter as ``GET /messages`` — so an inbox can render
 * message/unread badges at every level without paging any messages.
 */
export interface MessageCountsGet {
  counts?: MessageScopeCounts[];
  /** All visible messages */
  total?: number;
  /** All visible unread messages (own posts excluded) */
  unread?: number;
}

/**
 * Full conversation thread for a message.
 * 
 * Returns all messages sharing the same root, ordered by created_at.
 * Used by agents to get full conversation context for follow-up detection.
 */
export interface MessageThread {
  /** ID of the root message in the thread */
  root_message_id: string;
  /** All messages in the thread, ordered by created_at ascending */
  messages?: MessageList[];
  /** Total number of messages in the thread */
  total?: number;
}

/**
 * Multi-format error message.
 */
export interface ErrorMessageFormat {
  /** Plain text error message */
  plain: string;
  /** Markdown formatted message */
  markdown?: string | null;
  /** HTML formatted message */
  html?: string | null;
}