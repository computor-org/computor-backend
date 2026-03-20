/**

 * Auto-generated TypeScript interfaces from Pydantic models

 * Category: Websocket

 */



/**
 * Base class for all WebSocket events.
 */
export interface WSEventBase {
  type: string;
}

/**
 * Subscribe to one or more channels.
 */
export interface WSChannelSubscribe {
  type?: "channel:subscribe";
  /** Channels to subscribe to, e.g., ['submission_group:123'] */
  channels: string[];
}

/**
 * Unsubscribe from one or more channels.
 */
export interface WSChannelUnsubscribe {
  type?: "channel:unsubscribe";
  /** Channels to unsubscribe from */
  channels: string[];
}

/**
 * User started typing in a channel.
 */
export interface WSTypingStart {
  type?: "typing:start";
  /** Channel where user is typing, e.g., 'submission_group:123' */
  channel: string;
}

/**
 * User stopped typing in a channel.
 */
export interface WSTypingStop {
  type?: "typing:stop";
  /** Channel where user stopped typing */
  channel: string;
}

/**
 * Mark a message as read.
 */
export interface WSReadMark {
  type?: "read:mark";
  /** Channel the message belongs to */
  channel: string;
  /** ID of the message to mark as read */
  message_id: string;
}

/**
 * Keep-alive ping from client.
 */
export interface WSPing {
  type?: "system:ping";
}

/**
 * Confirmation of successful subscription.
 */
export interface WSChannelSubscribed {
  type?: "channel:subscribed";
  /** Channels successfully subscribed to */
  channels: string[];
}

/**
 * Confirmation of successful unsubscription.
 */
export interface WSChannelUnsubscribed {
  type?: "channel:unsubscribed";
  /** Channels successfully unsubscribed from */
  channels: string[];
}

/**
 * Subscription error for a specific channel.
 */
export interface WSChannelError {
  type?: "channel:error";
  /** Channel that failed */
  channel: string;
  /** Error reason */
  reason: string;
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

/**
 * Typing status update for a user in a channel.
 */
export interface WSTypingUpdate {
  type?: "typing:update";
  /** Channel where typing status changed */
  channel: string;
  /** ID of the user */
  user_id: string;
  /** Display name of the user */
  user_name?: string | null;
  /** Whether the user is currently typing */
  is_typing: boolean;
}

/**
 * Read receipt notification (only for submission_group scope).
 */
export interface WSReadUpdate {
  type?: "read:update";
  /** Channel (submission_group only) */
  channel: string;
  /** ID of the message that was read */
  message_id: string;
  /** ID of the user who read the message */
  user_id: string;
}

/**
 * Keep-alive pong response.
 */
export interface WSPong {
  type?: "system:pong";
  timestamp?: string;
}

/**
 * General error event.
 */
export interface WSError {
  type?: "system:error";
  /** Error code */
  code: string;
  /** Human-readable error message */
  message: string;
}

/**
 * Connection established confirmation.
 */
export interface WSConnected {
  type?: "system:connected";
  /** ID of the authenticated user */
  user_id: string;
}

/**
 * Maintenance mode has been activated.
 */
export interface WSMaintenanceActivated {
  type?: "maintenance:activated";
  active?: boolean;
  /** Maintenance message for users */
  message: string;
  /** ISO8601 timestamp of activation */
  activated_at: string;
}

/**
 * Maintenance mode has been deactivated.
 */
export interface WSMaintenanceDeactivated {
  type?: "maintenance:deactivated";
  active?: boolean;
  message?: string;
}

/**
 * Maintenance has been scheduled for a future time.
 */
export interface WSMaintenanceScheduled {
  type?: "maintenance:scheduled";
  /** ISO8601 datetime of planned maintenance */
  scheduled_at: string;
  /** Schedule message for users */
  message: string;
}

/**
 * Scheduled maintenance has been cancelled.
 */
export interface WSMaintenanceCancelled {
  type?: "maintenance:cancelled";
  message?: string;
}

/**
 * Countdown reminder for upcoming scheduled maintenance.
 */
export interface WSMaintenanceReminder {
  type?: "maintenance:reminder";
  /** Minutes until maintenance begins */
  minutes_remaining: number;
  /** ISO8601 datetime of planned maintenance */
  scheduled_at: string;
  /** Maintenance message for users */
  message: string;
}

/**
 * Deployment status transition (e.g., pending -> deploying -> deployed/failed).
 */
export interface WSDeploymentStatusChanged {
  type?: "deployment:status_changed";
  /** Channel (course:{course_id}) */
  channel: string;
  /** ID of the course */
  course_id: string;
  /** ID of the course content */
  course_content_id: string;
  /** ID of the deployment */
  deployment_id: string;
  /** Status before the change */
  previous_status: string;
  /** Status after the change */
  new_status: string;
  /** Semantic version tag */
  version_tag?: string | null;
  /** Example identifier path */
  example_identifier?: string | null;
  /** Error or status message */
  deployment_message?: string | null;
  /** ISO8601 timestamp of deployment completion */
  deployed_at?: string | null;
  /** Temporal workflow ID */
  workflow_id?: string | null;
  /** ISO8601 timestamp of the event */
  timestamp: string;
}

/**
 * Example was assigned to course content by lecturer.
 */
export interface WSDeploymentAssigned {
  type?: "deployment:assigned";
  /** Channel (course:{course_id}) */
  channel: string;
  /** ID of the course */
  course_id: string;
  /** ID of the course content */
  course_content_id: string;
  /** ID of the deployment */
  deployment_id: string;
  /** Example identifier path */
  example_identifier?: string | null;
  /** Semantic version tag */
  version_tag: string;
  /** Current deployment status */
  deployment_status: string;
  /** ISO8601 timestamp of the event */
  timestamp: string;
}

/**
 * Example was unassigned from course content by lecturer.
 */
export interface WSDeploymentUnassigned {
  type?: "deployment:unassigned";
  /** Channel (course:{course_id}) */
  channel: string;
  /** ID of the course */
  course_id: string;
  /** ID of the course content */
  course_content_id: string;
  /** Previously assigned example identifier */
  previous_example_identifier?: string | null;
  /** Previously assigned version tag */
  previous_version_tag?: string | null;
  /** ISO8601 timestamp of the event */
  timestamp: string;
}

/**
 * Course content was created, updated, or deleted.
 */
export interface WSCourseContentUpdated {
  type?: "course:content_updated";
  /** Channel (course:{course_id}) */
  channel: string;
  /** ID of the course */
  course_id: string;
  /** ID of the course content */
  course_content_id: string;
  /** Type of change: created, updated, deleted, reordered */
  change_type: string;
  /** ISO8601 timestamp of the event */
  timestamp: string;
}