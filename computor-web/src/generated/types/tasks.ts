/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Tasks

 */



import type { Repository } from './common';



/**
 * Task execution result container.
 */
export interface TaskResult {
  task_id: string;
  status: TaskStatus;
  result?: any | null;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  progress?: Record<string, any> | null;
}

/**
 * Task submission request.
 */
export interface TaskSubmission {
  task_name: string;
  parameters?: Record<string, any>;
  queue?: string;
  workflow_id?: string | null;
  delay?: number | null;
}

/**
 * Task information for status queries.
 */
export interface TaskInfo {
  task_id: string;
  task_name: string;
  status: TaskStatus;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  progress?: Record<string, any> | null;
  error?: string | null;
  worker?: string | null;
  queue?: string | null;
  retries?: number | null;
  args?: any | null;
  kwargs?: Record<string, any> | null;
  short_task_id?: string | null;
  status_display?: string | null;
  completed_at?: string | null;
  has_result?: boolean | null;
  result_available?: string | null;
  duration?: string | null;
  workflow_id?: string | null;
  run_id?: string | null;
  execution_time?: string | null;
  history_length?: number | null;
}

/**
 * Task tracking entry stored in Redis for permission-aware task access.
 * 
 * This model stores permission-relevant metadata about tasks, allowing
 * non-admin users to query tasks they have access to.
 */
export interface TaskTrackerEntry {
  workflow_id: string;
  task_name: string;
  created_at: string;
  created_by: string;
  user_id?: string | null;
  course_id?: string | null;
  organization_id?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  description?: string | null;
}

export interface TestJob {
  user_id: string;
  course_member_id: string;
  course_content_id: string;
  testing_service_id: string;
  testing_service_slug: string;
  testing_service_type_path: string;
  module: Repository;
  reference?: Repository | null;
}

/**
 * Response with task ID for async operation.
 */
export interface TaskResponse {
  task_id: string;
  status: string;
  message: string;
}



export type TaskStatus = "queued" | "started" | "finished" | "failed" | "deferred" | "cancelled";