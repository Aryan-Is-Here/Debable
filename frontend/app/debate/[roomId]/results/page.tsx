import type { Metadata } from "next";

import { RatingForm } from "@/components/rating-form";
import { mockDebateRoom } from "@/lib/mock/debate";

export const metadata: Metadata = {
  title: "Rate your debate",
};

interface ResultsPageProps {
  params: Promise<{ roomId: string }>;
}

export default async function ResultsPage({ params }: ResultsPageProps) {
  // Phase 1: any roomId resolves to the demo room.
  await params;

  return (
    <div className="mx-auto w-full max-w-md px-4 py-16 sm:px-6">
      <RatingForm room={mockDebateRoom} />
    </div>
  );
}
