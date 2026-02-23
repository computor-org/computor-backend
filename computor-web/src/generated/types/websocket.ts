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