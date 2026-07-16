/**
 * Self-update types — hand-written mirror of computor_types/update.py
 * (SystemUpdateState / SystemUpdateStatusGet / SystemUpdateTriggerResponse).
 * Kept here (like auth.ts/consent.ts) because the generated-types pipeline
 * is regenerated wholesale; fold these into src/generated/types at the next
 * full regeneration.
 */

export type SystemUpdateStatus =
  | 'idle'
  | 'requested'
  | 'running'
  | 'success'
  | 'failed'
  | 'rolled_back';

export interface SystemUpdateState {
  status: SystemUpdateStatus;
  /** preflight | checking | checking_out | building | entering_maintenance |
   *  starting | health_check | finalizing | rolling_back */
  phase: string;
  message: string;
  from_commit: string | null;
  to_commit: string | null;
  requested_by: string | null;
  requested_by_name: string | null;
  requested_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface SystemUpdateStatusGet {
  update_enabled: boolean;
  running_commit: string;
  running_branch: string;
  /** Configured deployment repo URL (credentials stripped). */
  repo_url: string;
  tracked_branch: string;
  remote_commit: string | null;
  remote_checked_at: string | null;
  remote_error: string | null;
  update_available: boolean;
  /** Whether the updater sidecar heartbeat is live (always false in dev). */
  updater_online: boolean;
  state: SystemUpdateState;
}

export interface SystemUpdateTriggerResponse {
  status: string;
  requested_at: string;
}
