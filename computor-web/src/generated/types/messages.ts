/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Messages

 */



import type { MessageAuthor, MessageAuthorCourseMember } from './auth';



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
  /** Filter by tags in title (e.g., ['ai', 'ai-help', 'review']). Without # prefix. */
  tags?: string[] | null;
  /** True = must match ALL tags (AND), False = match ANY tag (OR) */
  tags_match_all?: boolean | null;
  /** Filter by tag prefix (e.g., 'ai' matches #ai, #ai-help, #ai-response, etc.) */
  tag_scope?: string | null;
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