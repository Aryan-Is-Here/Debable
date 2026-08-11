/**
 * Matchmaking API client.
 *
 * The queue lives server-side; the Waiting Room polls `getMatchState` until it flips from
 * `queued` to `matched`. See `docs/PROJECT-HANDBOOK.md` conflict #2 for why polling rather
 * than a socket.
 */

import type { DebateRoom, Topic } from "@/lib/types";
import { apiRequest } from "@/services/api-client";

export type MatchStatus = "idle" | "queued" | "matched";

export interface MatchState {
  status: MatchStatus;
  topic: Topic | null;
  /** ISO-8601 timestamp of when the caller joined the queue. */
  queuedAt: string | null;
  waitingCount: number;
  room: DebateRoom | null;
}

export async function joinQueue(topicId: string, token: string | null): Promise<MatchState> {
  return apiRequest<MatchState>("/match", { method: "POST", body: { topicId }, token });
}

export async function getMatchState(
  token: string | null,
  signal?: AbortSignal,
): Promise<MatchState> {
  return apiRequest<MatchState>("/match", { token, signal });
}

export async function leaveQueue(token: string | null): Promise<MatchState> {
  return apiRequest<MatchState>("/match", { method: "DELETE", token });
}

export async function getRoom(roomId: string, token: string | null): Promise<DebateRoom> {
  return apiRequest<DebateRoom>(`/rooms/${roomId}`, { token });
}

export async function endRoom(roomId: string, token: string | null): Promise<DebateRoom> {
  return apiRequest<DebateRoom>(`/rooms/${roomId}/end`, { method: "POST", token });
}

export const matchKeys = {
  state: ["match", "state"] as const,
  room: (id: string) => ["match", "room", id] as const,
};
