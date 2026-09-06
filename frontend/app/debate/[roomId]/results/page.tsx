import type { Metadata } from "next";

import { ResultsLoader } from "@/components/results-loader";

export const metadata: Metadata = {
  title: "Rate your debate",
};

interface ResultsPageProps {
  params: Promise<{ roomId: string }>;
}

export default async function ResultsPage({ params }: ResultsPageProps) {
  const { roomId } = await params;

  return (
    <div className="mx-auto w-full max-w-md px-4 py-16 sm:px-6">
      <ResultsLoader roomId={roomId} />
    </div>
  );
}
