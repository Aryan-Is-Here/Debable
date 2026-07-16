import type { Metadata } from "next";

import { WaitingRoom } from "@/components/waiting-room";
import { mockDebateRoom } from "@/lib/mock/debate";

export const metadata: Metadata = {
  title: "Finding an opponent",
};

export default function WaitingPage() {
  // Phase 1: use the fixed demo room. Real topic-based matchmaking is Phase 4.
  const { topic, opponent, id } = mockDebateRoom;

  return <WaitingRoom topic={topic} opponent={opponent} roomId={id} />;
}
