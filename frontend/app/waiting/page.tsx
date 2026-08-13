import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { WaitingRoom } from "@/components/waiting-room";

export const metadata: Metadata = {
  title: "Finding an opponent",
};

interface WaitingPageProps {
  searchParams: Promise<{ topic?: string }>;
}

export default async function WaitingPage({ searchParams }: WaitingPageProps) {
  const { topic } = await searchParams;

  // Reaching the queue without a topic means someone edited the URL — there is nothing to
  // wait for, so send them to pick one.
  if (!topic) redirect("/browse");

  return <WaitingRoom topicId={topic} />;
}
