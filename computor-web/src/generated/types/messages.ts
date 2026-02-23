/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Messages

 */



import type { MessageAuthor, MessageAuthorCourseMember } from './auth';



export interface MessageCreate {
  parent_id?: string | null;
  level?: number;
  title: string;
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
  title: string;
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
  title: string;
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
  course_id_all_messages?: boolean | null;
  scope?: "global" | "organization" | "course_family" | "course" | "course_content" | "course_group" | "submission_group" | "course_member" | "user" | null;
  /** Filter messages created at or after this datetime (inclusive) */
  created_after?: string | null;
  /** Filter messages created at or before this datetime (inclusive) */
  created_before?: string | null;
  /** Filter by read status: True = unread only, False = read only, None = all */
  unread?: boolean | null;
  /** Filter by tags in title (e.g., ['ai::request', 'priority::high']) */
  tags?: string[] | null;
  /** True = must match ALL tags (AND), False = match ANY tag (OR) */
  tags_match_all?: boolean | null;
  /** Filter by tag scope prefix (e.g., 'ai' matches any #ai::* tag) */
  tag_scope?: string | null;
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

/**
 * New message created in a channel.
 */
export interface WSMessageNew {
  type?: "message:new";
  /** Channel the message was posted to */
  channel: string;
  /** Message data (MessageGet serialized) */
  data: any;
}

/**
 * Message was updated.
 */
export interface WSMessageUpdate {
  type?: "message:update";
  /** Channel the message belongs to */
  channel: string;
  /** ID of the updated message */
  message_id: string;
  /** Updated message data (MessageGet serialized) */
  data: any;
}

/**
 * Message was deleted.
 */
export interface WSMessageDelete {
  type?: "message:delete";
  /** Channel the message belonged to */
  channel: string;
  /** ID of the deleted message */
  message_id: string;
}