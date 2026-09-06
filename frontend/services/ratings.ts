/**
 * Rating and profile API clients.
 *
 * `getRatingState` exists so the results screen can ask before rendering its form: a second
 * visit should show what was submitted rather than an empty form the server will refuse.
 */

import type { ID, UserProfile, UserSummary } from "@/lib/types";
import { apiRequest } from "@/services/api-client";

/** Mirrors `RatingCreate`/`RatingRead` in `backend/app/schemas/rating.py`. */
export interface Rating {
  id: ID;
  roomId: ID;
  reviewerId: ID;
  reviewedUserId: ID;
  score: number;
  comment: string | null;
  createdAt: string;
}

export interface RatingState {
  submitted: boolean;
  rating: Rating | null;
}

export interface WireHistoryEntry {
  id: ID;
  topicTitle: string;
  opponent: UserSummary;
  ratingReceived: number | null;
  date: string;
}

/** The profile as the backend sends it. `createdTopics` is added client-side — see below. */
export interface WireProfile {
  user: UserSummary;
  joinedAt: string;
  debatesCount: number;
  /** Null until somebody has rated this user. Not a zero, which would read as terrible. */
  averageRating: number | null;
  history: WireHistoryEntry[];
}

export const MAX_COMMENT_LENGTH = 300;

export async function getRatingState(
  roomId: string,
  token: string | null,
): Promise<RatingState> {
  return apiRequest<RatingState>(`/rooms/${roomId}/rating`, { token });
}

export async function submitRating(
  roomId: string,
  input: { score: number; comment?: string },
  token: string | null,
): Promise<Rating> {
  return apiRequest<Rating>(`/rooms/${roomId}/rating`, {
    method: "POST",
    body: input,
    token,
  });
}

export async function getProfile(token: string | null): Promise<WireProfile> {
  return apiRequest<WireProfile>("/profile", { token });
}

/**
 * Widen the wire profile to the view-model the Profile screen renders.
 *
 * `createdTopics` is not part of the profile response: topics already have their own
 * endpoint with filtering and paging, so the screen asks for them separately rather than
 * having a second, subtly different copy of that query embedded here.
 */
export function toUserProfile(
  wire: WireProfile,
  createdTopics: UserProfile["createdTopics"],
): UserProfile {
  return {
    user: wire.user,
    joinedAt: wire.joinedAt,
    debatesCount: wire.debatesCount,
    averageRating: wire.averageRating,
    createdTopics,
    history: wire.history.map((entry) => ({
      id: entry.id,
      topicTitle: entry.topicTitle,
      opponent: entry.opponent,
      ratingReceived: entry.ratingReceived,
      date: entry.date,
    })),
  };
}

export const ratingKeys = {
  state: (roomId: string) => ["rating", "state", roomId] as const,
  profile: ["rating", "profile"] as const,
};
