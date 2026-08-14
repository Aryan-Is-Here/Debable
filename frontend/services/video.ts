/**
 * Video token client.
 *
 * The browser never holds LiveKit credentials — it asks the backend for a token scoped to
 * one room and one identity, and that token is all it ever sees.
 */

import { apiRequest } from "@/services/api-client";

export interface RoomToken {
  /** LiveKit server URL (`wss://…`). */
  url: string;
  /** Short-lived JWT granting join access to this debate. */
  token: string;
  roomName: string;
}

export async function getRoomToken(roomId: string, authToken: string | null): Promise<RoomToken> {
  return apiRequest<RoomToken>(`/rooms/${roomId}/token`, { method: "POST", token: authToken });
}

export const videoKeys = {
  token: (roomId: string) => ["video", "token", roomId] as const,
};
