/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Update

 */



/**
 * State of the last (or currently running) self-update run.
 */
export interface SystemUpdateState {
  /** idle | requested | running | success | failed | rolled_back */
  status?: string;
  /** Progress within a run: preflight | checking | checking_out | building | entering_maintenance | starting | health_check | finalizing | rolling_back */
  phase?: string;
  message?: string;
  from_commit?: string | null;
  to_commit?: string | null;
  requested_by?: string | null;
  requested_by_name?: string | null;
  requested_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
}

/**
 * A pending one-shot scheduled update (fired by the updater sidecar).
 */
export interface SystemUpdateSchedule {
  scheduled_at: string;
  scheduled_by?: string | null;
  scheduled_by_name?: string | null;
  created_at?: string | null;
}

/**
 * How the most recent schedule was resolved.
 */
export interface SystemUpdateScheduleResult {
  /** fired | missed | skipped_lock */
  outcome?: string;
  scheduled_at?: string | null;
  resolved_at?: string | null;
  detail?: string | null;
}

/**
 * Running vs. remote version, updater availability, and last run state.
 */
export interface SystemUpdateStatusGet {
  update_enabled?: boolean;
  running_commit?: string;
  running_branch?: string;
  /** Configured deployment repo URL (credentials stripped). */
  repo_url?: string;
  tracked_branch?: string;
  remote_commit?: string | null;
  remote_checked_at?: string | null;
  remote_error?: string | null;
  update_available?: boolean;
  /** Whether the updater sidecar heartbeat is live (always false in dev). */
  updater_online?: boolean;
  state?: SystemUpdateState;
  schedule?: SystemUpdateSchedule | null;
  last_schedule_result?: SystemUpdateScheduleResult | null;
}

/**
 * Response to a successfully queued update request.
 */
export interface SystemUpdateTriggerResponse {
  status?: string;
  requested_at: string;
}

/**
 * Request to schedule a one-shot update at a future time.
 */
export interface SystemUpdateScheduleRequest {
  /** ISO8601 datetime (UTC assumed if naive). */
  scheduled_at: string;
}

/**
 * Response to a successfully stored update schedule.
 */
export interface SystemUpdateScheduleResponse {
  status?: string;
  scheduled_at: string;
  scheduled_by_name?: string | null;
}