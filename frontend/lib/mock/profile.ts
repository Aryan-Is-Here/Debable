import type { UserProfile } from "@/lib/types";
import { mockUsers } from "@/lib/mock/users";
import { mockTopics } from "@/lib/mock/topics";
import { currentUser } from "@/lib/mock/debate";

/** Profile fixture for the local viewer (ava). */
export const mockProfile: UserProfile = {
  user: currentUser,
  joinedAt: "2026-05-14T00:00:00Z",
  debatesCount: 12,
  averageRating: 4.3,
  createdTopics: mockTopics.filter((t) => t.creator.id === currentUser.id),
  history: [
    {
      id: "h1",
      topicTitle: "Will AI create more jobs than it destroys?",
      opponent: mockUsers.marcus,
      ratingReceived: 5,
      date: "2026-07-13T15:00:00Z",
    },
    {
      id: "h2",
      topicTitle: "Remote work is better for productivity than the office",
      opponent: mockUsers.sofia,
      ratingReceived: 4,
      date: "2026-07-10T19:30:00Z",
    },
    {
      id: "h3",
      topicTitle: "Universal Basic Income should replace welfare programs",
      opponent: mockUsers.diego,
      ratingReceived: null,
      date: "2026-07-06T12:10:00Z",
    },
  ],
};
