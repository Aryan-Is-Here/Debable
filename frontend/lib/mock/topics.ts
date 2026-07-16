import type { Topic } from "@/lib/types";
import { mockUsers } from "@/lib/mock/users";

/**
 * Mock debate topics for Phase 1 screens. Kept small and varied across
 * categories so lists, badges, and empty/active states are all exercised.
 */
export const mockTopics: Topic[] = [
  {
    id: "t_ai_jobs",
    title: "Will AI create more jobs than it destroys?",
    description:
      "Automation is reshaping the labor market. Does AI ultimately expand opportunity, or hollow out the middle?",
    status: "active",
    creator: mockUsers.ava,
    category: "Technology",
    activeDebaters: 7,
    createdAt: "2026-07-09T14:20:00Z",
  },
  {
    id: "t_ubi",
    title: "Universal Basic Income should replace welfare programs",
    description:
      "A no-strings monthly payment versus targeted, means-tested support. Which better serves society?",
    status: "active",
    creator: mockUsers.marcus,
    category: "Economics",
    activeDebaters: 4,
    createdAt: "2026-07-10T09:05:00Z",
  },
  {
    id: "t_social_age",
    title: "Social media should have a minimum age of 16",
    description:
      "Balancing youth mental health against access, autonomy, and enforcement realities.",
    status: "open",
    creator: mockUsers.priya,
    category: "Society",
    activeDebaters: 2,
    createdAt: "2026-07-11T18:40:00Z",
  },
  {
    id: "t_nuclear",
    title: "Nuclear power is essential to fighting climate change",
    description:
      "Reliable low-carbon baseload versus cost, waste, and safety concerns. Where should we invest?",
    status: "open",
    creator: mockUsers.diego,
    category: "Science",
    activeDebaters: 3,
    createdAt: "2026-07-11T21:15:00Z",
  },
  {
    id: "t_remote_work",
    title: "Remote work is better for productivity than the office",
    description:
      "Focus and flexibility versus collaboration and culture. Does distributed work win on output?",
    status: "active",
    creator: mockUsers.sofia,
    category: "Work",
    activeDebaters: 5,
    createdAt: "2026-07-08T11:00:00Z",
  },
  {
    id: "t_space",
    title: "Public money should fund space exploration",
    description:
      "Long-term scientific payoff versus pressing needs on Earth. Is public spending on space justified?",
    status: "archived",
    creator: mockUsers.kenji,
    category: "Science",
    activeDebaters: 0,
    createdAt: "2026-06-30T16:30:00Z",
  },
];

/** Topics surfaced on the Home screen — most active first, excluding archived. */
export function getTrendingTopics(limit = 4): Topic[] {
  return mockTopics
    .filter((topic) => topic.status !== "archived")
    .sort((a, b) => b.activeDebaters - a.activeDebaters)
    .slice(0, limit);
}

/** Unique topic categories, alphabetically sorted, for the browse filter. */
export function getCategories(): string[] {
  return Array.from(new Set(mockTopics.map((topic) => topic.category))).sort();
}
