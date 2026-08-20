/**
 * Chat API client and socket protocol.
 *
 * History is REST and delivery is a WebSocket (see `docs/PROJECT-HANDBOOK.md` conflict #3).
 * The split matters here: `getMessages` still works when the socket is down, so a broken
 * connection degrades the chat to read-only rather than blank.
 *
 * The wire carries `senderId` rather than the viewer-relative `author` field in
 * `lib/types.ts`. One broadcast frame reaches both debaters, and "you" would mean the
 * opposite thing on each side — so the mapping happens here, per client.
 */

import type { ChatMessage, ID } from "@/lib/types";
import { API_BASE_URL, apiRequest } from "@/services/api-client";

/** A message exactly as the backend stores and sends it. */
export interface WireMessage {
  id: ID;
  roomId: ID;
  senderId: ID;
  content: string;
  createdAt: string;
}

interface MessageListResponse {
  messages: WireMessage[];
}

/** Frames the server sends. Discriminated on `type`, matching `app/schemas/chat.py`. */
export type ServerFrame =
  | { type: "ready"; roomId: ID; userId: ID }
  | { type: "message"; message: WireMessage }
  | { type: "error"; code: string; message: string };

/** Frames the client sends. */
export type ClientFrame =
  | { type: "auth"; token: string }
  | { type: "message"; content: string };

/** Matches `MAX_MESSAGE_LENGTH` in `backend/app/schemas/chat.py`. */
export const MAX_MESSAGE_LENGTH = 2000;

export async function getMessages(
  roomId: string,
  token: string | null,
  signal?: AbortSignal,
): Promise<WireMessage[]> {
  const body = await apiRequest<MessageListResponse>(`/rooms/${roomId}/messages`, {
    token,
    signal,
  });
  return body.messages;
}

/**
 * The socket URL for a room's chat.
 *
 * Derived from `API_BASE_URL` rather than configured separately, so there is one place to
 * point at a different backend and no way for the two to disagree. `http` becomes `ws` and
 * `https` becomes `wss`; anything already using a ws scheme is left alone.
 */
export function chatSocketUrl(roomId: string): string {
  const url = new URL(`${API_BASE_URL}/rooms/${roomId}/chat`);
  if (url.protocol === "http:") url.protocol = "ws:";
  else if (url.protocol === "https:") url.protocol = "wss:";
  return url.toString();
}

/**
 * Map a stored message onto the view-model the UI renders.
 *
 * `youId` is the local user's id, which the server sends in the `ready` frame — the client
 * cannot infer it from the room alone without trusting its own copy of `room.you`.
 */
export function toChatMessage(wire: WireMessage, youId: string | null): ChatMessage {
  return {
    id: wire.id,
    author: wire.senderId === youId ? "you" : "opponent",
    content: wire.content,
    createdAt: wire.createdAt,
  };
}

export const chatKeys = {
  messages: (roomId: string) => ["chat", "messages", roomId] as const,
};
