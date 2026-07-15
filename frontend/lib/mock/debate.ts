import type { ChatMessage, DebateRoom, FactCheck } from "@/lib/types";
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

/** Seed chat history, including one prior AI fact-check result. */
export const mockMessages: ChatMessage[] = [
  {
    id: "m1",
    author: "opponent",
    content:
      "Automation has historically created more jobs than it destroyed — think ATMs and bank tellers.",
    createdAt: "2026-07-13T15:01:10Z",
  },
  {
    id: "m2",
    author: "you",
    content:
      "That's the common example, but AI targets cognitive work at a scale we haven't seen before.",
    createdAt: "2026-07-13T15:01:52Z",
  },
  {
    id: "m3",
    author: "opponent",
    content:
      "Studies show most occupations are augmented, not fully replaced.",
    createdAt: "2026-07-13T15:02:30Z",
  },
  {
    id: "m4",
    author: "system",
    content: "",
    createdAt: "2026-07-13T15:03:00Z",
    factCheck: {
      id: "fc_seed",
      claim: "ATMs increased the total number of bank teller jobs.",
      verdict: "misleading",
      explanation:
        "Teller employment held roughly steady for a period as branches expanded, but has declined over the long term. The claim oversimplifies a mixed trend.",
      sources: [
        {
          title: "Bureau of Labor Statistics — Tellers",
          url: "https://www.bls.gov/ooh/office-and-administrative-support/tellers.htm",
        },
      ],
      createdAt: "2026-07-13T15:03:00Z",
    },
  },
];

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
