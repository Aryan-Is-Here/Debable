import type { DebateRoom } from "@/lib/types";
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
