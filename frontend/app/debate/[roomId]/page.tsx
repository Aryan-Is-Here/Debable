import type { Metadata } from "next";

import { DebateRoomLoader } from "@/components/debate-room-loader";

export const metadata: Metadata = {
  title: "Debate room",
};

interface DebatePageProps {
  params: Promise<{ roomId: string }>;
}

export default async function DebatePage({ params }: DebatePageProps) {
  const { roomId } = await params;

  return <DebateRoomLoader roomId={roomId} />;
}
