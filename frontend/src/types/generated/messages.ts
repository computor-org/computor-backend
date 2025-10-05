/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Messages

 */



import type { MessageAuthor } from './auth';



export interface MessageCreate {
  parent_id?: string | null;
  level?: number;
  title: string;
  content: string;
  user_id?: string | null;
  course_member_id?: string | null;
  submission_group_id?: string | null;
  course_group_id?: string | null;
  course_content_id?: string | null;
  course_id?: string | null;
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
  /** Author details */
  author?: MessageAuthor | null;
  is_read?: boolean;
  user_id?: string | null;
  course_member_id?: string | null;
  submission_group_id?: string | null;
  course_group_id?: string | null;
  course_content_id?: string | null;
  course_id?: string | null;
  /** Determine message scope based on target fields (priority order) */
  scope: "user" | "course_member" | "submission_group" | "course_group" | "course_content" | "course";
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
  /** Author details */
  author?: MessageAuthor | null;
  is_read?: boolean;
  user_id?: string | null;
  course_member_id?: string | null;
  submission_group_id?: string | null;
  course_group_id?: string | null;
  course_content_id?: string | null;
  course_id?: string | null;
  /** Determine message scope based on target fields (priority order) */
  scope: "user" | "course_member" | "submission_group" | "course_group" | "course_content" | "course";
}

export interface MessageQuery {
  skip?: number | null;
  limit?: number | null;
  id?: string | null;
  parent_id?: string | null;
  author_id?: string | null;
  user_id?: string | null;
  course_member_id?: string | null;
  submission_group_id?: string | null;
  course_group_id?: string | null;
  course_content_id?: string | null;
  course_id?: string | null;
  course_id_all_messages?: boolean | null;
  scope?: "user" | "course_member" | "submission_group" | "course_group" | "course_content" | "course" | null;
}