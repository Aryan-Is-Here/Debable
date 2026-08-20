import type { DebateRoom, FactCheck } from "@/lib/types";
import { mockUsers } from "@/lib/mock/users";
import { mockTopics } from "@/lib/mock/topics";

/** The local viewer in the prototype. */
export const currentUser = mockUsers.ava;

/**
 * A single mock debate room used to drive the Debate Room and Results screens.
 * Pairs the current user against an opponent on a fixed topic.
 */
export const mockDebateRoom: DebateRoom = {
  id: "room_demo",
  topic: mockTopics[0], // "Will AI create more jobs than it destroys?"
  you: currentUser,
  opponent: mockUsers.marcus,
  startedAt: "2026-07-13T15:00:00Z",
};

/**
 * Deterministic mock fact-check generator. Stands in for the AI service so the
 * UI can be exercised without a backend. Cycles a verdict from the claim length
 * to avoid randomness (which is unavailable in some execution contexts).
 */
export function mockFactCheck(claim: string): FactCheck {
  const verdicts = ["true", "false", "misleading", "unverified"] as const;
  const verdict = verdicts[claim.trim().length % verdicts.length];

  const explanations: Record<(typeof verdicts)[number], string> = {
    true: "Trusted sources corroborate this claim.",
    false: "Trusted sources contradict this claim.",
    misleading: "The claim contains a kernel of truth but omits key context.",
    unverified: "No trusted source could confirm or refute this claim.",
  };

  return {
    id: `fc_${claim.trim().length}`,
    claim: claim.trim(),
    verdict,
    explanation: explanations[verdict],
    sources: [
      { title: "Example trusted source", url: "https://example.org/source" },
    ],
    createdAt: mockDebateRoom.startedAt,
  };
}
