/**
 * Client for maintenance mode API.
 * Endpoint: /system/maintenance
 */

import { APIClient, apiClient } from 'api/client';
import { BaseEndpointClient } from '@/src/generated/clients/baseClient';

export interface MaintenanceStatus {
  active: boolean;
  message: string;
  activated_at: string | null;
  activated_by: string | null;
  activated_by_name: string | null;
  scheduled_at: string | null;
  scheduled_by: string | null;
  scheduled_by_name: string | null;
}

export class MaintenanceClient extends BaseEndpointClient {
  constructor(client: APIClient = apiClient) {
    super(client, '/system/maintenance');
  }

  async getStatus(): Promise<MaintenanceStatus> {
    return this.client.get<MaintenanceStatus>(this.buildPath('status'));
  }

  async activate(message: string, notifyWebsocket = true): Promise<void> {
    return this.client.post<void>(this.buildPath('activate'), {
      message,
      notify_websocket: notifyWebsocket,
    });
  }

  async deactivate(): Promise<void> {
    return this.client.post<void>(this.buildPath('deactivate'));
  }

  async schedule(scheduledAt: string, message: string, notifyWebsocket = true): Promise<void> {
    return this.client.post<void>(this.buildPath('schedule'), {
      scheduled_at: scheduledAt,
      message,
      notify_websocket: notifyWebsocket,
    });
  }

  async cancelSchedule(): Promise<void> {
    return this.client.delete<void>(this.buildPath('schedule'));
  }
}
