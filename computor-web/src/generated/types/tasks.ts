/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Tasks

 */



import type { Repository } from './common';



/**
 * Every environment variable read by the task / testing / worker layer.
 */
export interface WorkerSettings {
  api_url?: string;
  api_token?: string | null;
  system_git_email?: string;
  system_git_name?: string;
  example_cache_dir?: string;
  temporal_host?: string;
  temporal_port?: number;
  temporal_namespace?: string;
  temporal_tls_cert?: string | null;
  temporal_tls_key?: string | null;
  temporal_tls_ca?: string | null;
  activity_executor_max_workers?: number;
  max_concurrent_activities?: number | null;
  graceful_shutdown_seconds?: number;
  coder_registry_host?: string | null;
  coder_url?: string | null;
  coder_registry_container?: string;
  docker_socket_path?: string;
  testing_executable?: string | null;
  runtime_environment?: string;
  running_in_docker?: string | null;
}

/**
 * Task execution result container.
 */
export interface TaskResult {
  task_id: string;
  status: TaskStatus;
  result?: unknown | null;
  error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  progress?: Record<string, unknown> | null;
}

/**
 * Task submission request.
 */
export interface TaskSubmission {
  task_name: string;
  parameters?: Record<string, unknown>;
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
  progress?: Record<string, unknown> | null;
  error?: string | null;
  worker?: string | null;
  queue?: string | null;
  retries?: number | null;
  args?: unknown | null;
  kwargs?: Record<string, unknown> | null;
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

export type ResultStatus = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7;