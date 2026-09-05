/**
 * Fact-check API client.
 *
 * History is REST and delivery is the chat socket, the same split as chat itself: the
 * verdict is pushed to both debaters over the socket, and `getFactChecks` restores it after
 * a reload.
 *
 * Requesting a check is a POST rather than a socket frame because it takes seconds and
 * spends a request from a small free-tier budget — it must not sit in the socket's receive
 * loop where it would block every chat message behind it.
 */

import type { FactCheck, ID } from "@/lib/types";
import { apiRequest } from "@/services/api-client";

/** A verdict exactly as the backend stores and sends it. */
export interface WireFactCheck {
  id: ID;
  roomId: ID;
  requesterId: ID;
  claim: string;
  verdict: FactCheck["verdict"];
  explanation: string;
  sources: { title: string; url: string }[];
  createdAt: string;
}

interface FactCheckListResponse {
  factChecks: WireFactCheck[];
}

/** Mirrors `ClaimStr` in `backend/app/schemas/fact_check.py`. */
export const MIN_CLAIM_LENGTH = 10;
export const MAX_CLAIM_LENGTH = 500;

export async function getFactChecks(
  roomId: string,
  token: string | null,
  signal?: AbortSignal,
): Promise<WireFactCheck[]> {
  const body = await apiRequest<FactCheckListResponse>(`/rooms/${roomId}/fact-checks`, {
    token,
    signal,
  });
  return body.factChecks;
}

export async function requestFactCheck(
  roomId: string,
  claim: string,
  token: string | null,
): Promise<WireFactCheck> {
  return apiRequest<WireFactCheck>(`/rooms/${roomId}/fact-check`, {
    method: "POST",
    body: { claim },
    token,
  });
}

/**
 * Map a stored verdict onto the view-model `FactCheckCard` already renders.
 *
 * `lib/types.ts` is unchanged from Phase 1 — the card has been drawing this shape from mock
 * data since before there was a backend.
 */
export function toFactCheck(wire: WireFactCheck): FactCheck {
  return {
    id: wire.id,
    claim: wire.claim,
    verdict: wire.verdict,
    explanation: wire.explanation,
    sources: wire.sources,
    createdAt: wire.createdAt,
  };
}

export const factCheckKeys = {
  list: (roomId: string) => ["fact-check", "list", roomId] as const,
};
