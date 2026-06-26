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
}

export interface MessageCreate {
  parent_id?: string | null;
  level?: number;
  /** Message title (optional, used for tags like #ai) */
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
  organization_id?: string | null;
  course_family_id?: string | null;
  course_id?: string | null;
  course_content_id?: string | null;
  course_group_id?: string | null;
  submission_group_id?: string | null;
  course_member_id?: string | null;
  user_id?: string | null;
  /** Determine message scope based on target fields (priority order: most specific first) */
  scope: "global" | "organization" | "course_family" | "course" | "course_content" | "course_group" | "submission_group" | "course_member" | "user";
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
  organization_id?: string | null;
  course_family_id?: string | null;
  course_id?: string | null;
  course_content_id?: string | null;
  course_group_id?: string | null;
  submission_group_id?: string | null;
  course_member_id?: string | null;
  user_id?: string | null;
  /** Determine message scope based on target fields (priority order: most specific first) */
  scope: "global" | "organization" | "course_family" | "course" | "course_content" | "course_group" | "submission_group" | "course_member" | "user";
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