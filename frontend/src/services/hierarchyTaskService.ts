/**
 * Service for managing hierarchy creation tasks (Organization → Course Family → Course).
 * 
 * This service provides task-based creation with GitLab integration,
 * allowing users to create entities asynchronously and monitor progress.
 */

import { apiClient } from './apiClient';

export interface GitLabCredentials {
  gitlab_url: string;
  gitlab_token: string;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface TaskStatus {
  task_id: string;
  task_name: string;
  status: 'PENDING' | 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'RETRY' | 'REVOKED';
  created_at: string;
  started_at?: string;
  finished_at?: string;
  progress?: {
    stage?: string;
    progress?: number;
    current?: number;
    total?: number;
  };
  error?: string;
}

// Backend TaskStatus enum values (from computor_backend.tasks.base.TaskStatus)
export type BackendTaskStatus = 
  | 'queued'     // TaskStatus.QUEUED
  | 'started'    // TaskStatus.STARTED
  | 'finished'   // TaskStatus.FINISHED
  | 'failed'     // TaskStatus.FAILED
  | 'deferred'   // TaskStatus.DEFERRED
  | 'cancelled'; // TaskStatus.CANCELLED

// Frontend display status
export type FrontendTaskStatus = 
  | 'pending'
  | 'running' 
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface TaskStatusResponse {
  status: BackendTaskStatus;
  message?: string;
  result?: any;
}

// Status mapping utility
export class TaskStatusMapper {
  static toFrontendStatus(backendStatus: BackendTaskStatus): FrontendTaskStatus {
    switch (backendStatus) {
      case 'queued':
      case 'deferred':
        return 'pending';
      case 'started':
        return 'running';
      case 'finished':
        return 'completed';
      case 'failed':
        return 'failed';
      case 'cancelled':
        return 'cancelled';
      default:
        return 'pending';
    }
  }

  static isCompleted(status: BackendTaskStatus): boolean {
    return ['finished', 'failed', 'cancelled'].includes(status);
  }

  static isSuccess(status: BackendTaskStatus): boolean {
    return status === 'finished';
  }

  static isFailed(status: BackendTaskStatus): boolean {
    return status === 'failed';
  }

  static isRunning(status: BackendTaskStatus): boolean {
    return status === 'started';
  }
}

export interface TaskResult {
  task_id: string;
  status: string;
  result?: any;
  error?: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  progress?: any;
}

export interface OrganizationTaskRequest {
  organization: {
    title: string;
    path: string;
    description?: string;
    organization_type: 'user' | 'community' | 'organization';
    number?: string;
    email?: string;
    telephone?: string;
    url?: string;
    street_address?: string;
    locality?: string;
    region?: string;
    postal_code?: string;
    country?: string;
  };
  gitlab: GitLabCredentials;
  parent_group_id: number;
}

export interface CourseFamilyTaskRequest {
  course_family: {
    title: string;
    path: string;
    description?: string;
    organization_id: string;
  };
  organization_id: string;
  gitlab?: GitLabCredentials;  // Optional - will use org's GitLab config if not provided
}

export interface CourseTaskRequest {
  course: {
    title: string;
    path: string;
    description?: string;
    course_family_id: string;
  };
  course_family_id: string;
  gitlab?: GitLabCredentials;  // Optional - will use course family's GitLab config if not provided
}

export interface HierarchyTaskRequest {
  organization: {
    title: string;
    path: string;
    description?: string;
    organization_type: 'user' | 'community' | 'organization';
  };
  course_family: {
    title: string;
    path: string;
    description?: string;
    organization_id: string;
  };
  course: {
    title: string;
    path: string;
    description?: string;
    course_family_id: string;
  };
  gitlab: GitLabCredentials;
  parent_group_id: number;
}

export class HierarchyTaskService {
  
  /**
   * Create an organization asynchronously with GitLab integration
   */
  static async createOrganization(request: OrganizationTaskRequest): Promise<TaskResponse> {
    try {
      const response = await apiClient.post<TaskResponse>('/system/deploy/organizations', request);
      return response;
    } catch (error: any) {
      console.error('Error creating organization task:', error);
      throw new Error(error.message || 'Failed to create organization task');
    }
  }

  /**
   * Create a course family asynchronously with GitLab integration
   */
  static async createCourseFamily(request: CourseFamilyTaskRequest): Promise<TaskResponse> {
    try {
      const response = await apiClient.post<TaskResponse>('/system/deploy/course-families', request);
      return response;
    } catch (error: any) {
      console.error('Error creating course family task:', error);
      throw new Error(error.message || 'Failed to create course family task');
    }
  }

  /**
   * Create a course asynchronously with GitLab integration
   */
  static async createCourse(request: CourseTaskRequest): Promise<TaskResponse> {
    try {
      const response = await apiClient.post<TaskResponse>('/system/deploy/courses', request);
      return response;
    } catch (error: any) {
      console.error('Error creating course task:', error);
      throw new Error(error.message || 'Failed to create course task');
    }
  }

  /**
   * Get task status from system endpoint
   */
  static async getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    try {
      const response = await apiClient.get<TaskStatusResponse>(`/tasks/${taskId}/status`);
      return response;
    } catch (error: any) {
      console.error('Error getting task status:', error);
      throw new Error(error.message || 'Failed to get task status');
    }
  }


  /**
   * Get task result (waits for completion)
   */
  static async getTaskResult(taskId: string): Promise<TaskResult> {
    try {
      const response = await apiClient.get<TaskResult>(`/tasks/${taskId}/result`);
      return response;
    } catch (error: any) {
      console.error('Error getting task result:', error);
      throw new Error(error.message || 'Failed to get task result');
    }
  }

  /**
   * Wait for task completion with polling
   */
  static async waitForTaskCompletion(
    taskId: string, 
    onProgress?: (status: TaskStatus) => void,
    pollInterval: number = 2000,
    maxWaitTime: number = 300000 // 5 minutes
  ): Promise<TaskResult> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < maxWaitTime) {
      try {
        const status = await this.getTaskStatus(taskId);
        
        // Convert TaskStatusResponse to TaskStatus for onProgress callback
        if (onProgress && status) {
          const taskStatus: TaskStatus = {
            task_id: taskId,
            task_name: 'hierarchy_creation',
            status: TaskStatusMapper.isSuccess(status.status) ? 'SUCCESS' : 
                   TaskStatusMapper.isFailed(status.status) ? 'FAILURE' : 
                   TaskStatusMapper.isRunning(status.status) ? 'PROGRESS' : 'PENDING',
            created_at: new Date().toISOString(),
            progress: status.message ? { stage: status.message } : undefined,
            error: TaskStatusMapper.isFailed(status.status) ? status.message : undefined
          };
          onProgress(taskStatus);
        }
        
        if (TaskStatusMapper.isCompleted(status.status)) {
          return {
            task_id: taskId,
            status: status.status,
            result: status.result,
            error: TaskStatusMapper.isFailed(status.status) ? status.message : undefined,
            created_at: new Date().toISOString(),
            finished_at: new Date().toISOString()
          };
        }
        
        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        
      } catch (error) {
        console.error('Error polling task status:', error);
        // Continue polling in case of temporary errors
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }
    
    throw new Error(`Task ${taskId} did not complete within ${maxWaitTime}ms`);
  }

  /**
   * Cancel a running task
   */
  static async cancelTask(taskId: string): Promise<void> {
    try {
      await apiClient.delete(`/tasks/${taskId}/cancel`);
    } catch (error: any) {
      console.error('Error cancelling task:', error);
      throw new Error(error.message || 'Failed to cancel task');
    }
  }
}