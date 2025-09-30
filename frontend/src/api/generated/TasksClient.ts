/**
 * Auto-generated client for TasksClient.
 * Endpoint: /tasks
 */

import type { TaskInfo, TaskResult, TaskSubmission } from 'types/generated';
import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from './baseClient';

export class TasksClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/tasks');
  }

  /**
   * List Tasks
   * List tasks with optional filtering and pagination.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * limit: Maximum number of tasks to return (1-1000)
   * offset: Number of tasks to skip for pagination
   * status: Optional status filter
   * Returns:
   * Dictionary containing:
   * - tasks: List of task information
   * - total: Total number of tasks
   * - limit: Applied limit
   * - offset: Applied offset
   * - has_more: Whether more tasks are available
   * Example:
   * GET /tasks?limit=10&offset=0&status=SUCCESS
   */
  async listTasksTasksGet({ limit, offset, status }: { limit?: number; offset?: number; status?: string | null }): Promise<Record<string, unknown> & Record<string, unknown>> {
    const queryParams: Record<string, unknown> = {
      limit,
      offset,
      status,
    };
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.basePath, { params: queryParams });
  }

  /**
   * Submit Task
   * Submit a task for asynchronous execution.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * submission: Task submission details
   * Returns:
   * Dictionary containing task_id and status
   * Raises:
   * HTTPException: If task type is not registered or submission fails
   */
  async submitTaskTasksSubmitPost({ body }: { body: TaskSubmission }): Promise<Record<string, unknown> & Record<string, string>> {
    return this.client.post<Record<string, unknown> & Record<string, string>>(this.buildPath('submit'), body);
  }

  /**
   * Get Task
   * Get task information by ID.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * task_id: Task ID
   * Returns:
   * Task information including status, timestamps, and metadata
   * Raises:
   * HTTPException: If task is not found
   */
  async getTaskTasksTaskIdGet({ taskId }: { taskId: string }): Promise<TaskInfo> {
    return this.client.get<TaskInfo>(this.buildPath(taskId));
  }

  /**
   * Delete Task
   * Delete a task from the database.
   * Admin only endpoint.
   * Note: Temporal doesn't support direct deletion of workflow history.
   * Use cancellation or retention policies instead.
   * Args:
   * permissions: Current user permissions
   * task_id: Task ID to delete
   * Returns:
   * Error message explaining limitation
   * Raises:
   * HTTPException: Always returns 501 Not Implemented for Temporal
   */
  async deleteTaskTasksTaskIdDelete({ taskId }: { taskId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath(taskId));
  }

  /**
   * Get Task Status
   * Get task execution status and information.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * task_id: Task ID
   * Returns:
   * Task information including status and progress
   * Raises:
   * HTTPException: If task is not found
   */
  async getTaskStatusTasksTaskIdStatusGet({ taskId }: { taskId: string }): Promise<TaskInfo> {
    return this.client.get<TaskInfo>(this.buildPath(taskId, 'status'));
  }

  /**
   * Get Task Result
   * Get task execution result.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * task_id: Task ID
   * Returns:
   * Task result including output data and any errors
   * Raises:
   * HTTPException: If task is not found
   */
  async getTaskResultTasksTaskIdResultGet({ taskId }: { taskId: string }): Promise<TaskResult> {
    return this.client.get<TaskResult>(this.buildPath(taskId, 'result'));
  }

  /**
   * Cancel Task
   * Cancel a queued or running task.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * task_id: Task ID
   * Returns:
   * Cancellation status
   * Raises:
   * HTTPException: If cancellation fails
   */
  async cancelTaskTasksTaskIdCancelDelete({ taskId }: { taskId: string }): Promise<void> {
    return this.client.delete<void>(this.buildPath(taskId, 'cancel'));
  }

  /**
   * List Task Types
   * Get list of available task types.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * Returns:
   * List of registered task names
   */
  async listTaskTypesTasksTypesGet(): Promise<string[]> {
    return this.client.get<string[]>(this.buildPath('types'));
  }

  /**
   * Get Worker Status
   * Get Temporal worker and queue status information.
   * Admin only endpoint.
   * Args:
   * permissions: Current user permissions
   * Returns:
   * Dictionary containing worker status, queue information, and connection details
   */
  async getWorkerStatusTasksWorkersStatusGet(): Promise<Record<string, unknown> & Record<string, unknown>> {
    return this.client.get<Record<string, unknown> & Record<string, unknown>>(this.buildPath('workers', 'status'));
  }
}
