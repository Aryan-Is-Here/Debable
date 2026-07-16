import type { Metadata } from "next";

import { DebateRoomView } from "@/components/debate-room-view";
import { mockDebateRoom, mockMessages } from "@/lib/mock/debate";

export const metadata: Metadata = {
  title: "Debate room",
};

interface DebatePageProps {
  params: Promise<{ roomId: string }>;
}

export default async function DebatePage({ params }: DebatePageProps) {
  // Phase 1: any roomId resolves to the demo room; real rooms arrive with the
  // backend in later phases.
  await params;

  return <DebateRoomView room={mockDebateRoom} initialMessages={mockMessages} />;
}
