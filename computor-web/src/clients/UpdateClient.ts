/**
 * Client for the self-update API.
 * Endpoint: /system/update
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';
import type {
  SystemUpdateScheduleResponse,
  SystemUpdateStatusGet,
  SystemUpdateTriggerResponse,
} from '@/src/types/update';

export class UpdateClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/system/update');
  }

  async getStatus(): Promise<SystemUpdateStatusGet> {
    return this.client.get<SystemUpdateStatusGet>(this.buildPath('status'));
  }

  /** Force-refresh the remote tip (ignores the 5-minute cache). */
  async checkNow(): Promise<SystemUpdateStatusGet> {
    return this.client.post<SystemUpdateStatusGet>(this.buildPath('check'));
  }

  /** Queue a self-update run (executed by the updater sidecar; prod only). */
  async triggerUpdate(): Promise<SystemUpdateTriggerResponse> {
    return this.client.post<SystemUpdateTriggerResponse>(this.buildPath());
  }

  /** Schedule a one-shot update (fired by the updater sidecar at the given time). */
  async scheduleUpdate(scheduledAt: string): Promise<SystemUpdateScheduleResponse> {
    return this.client.post<SystemUpdateScheduleResponse>(this.buildPath('schedule'), {
      scheduled_at: scheduledAt,
    });
  }

  /** Cancel a pending scheduled update. */
  async cancelSchedule(): Promise<void> {
    return this.client.delete<void>(this.buildPath('schedule'));
  }

  /** Clear a stuck update lock/state (admin recovery). */
  async reset(): Promise<void> {
    return this.client.post<void>(this.buildPath('reset'));
  }
}
