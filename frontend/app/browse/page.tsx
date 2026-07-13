import type { Metadata } from "next";

import { TopicBrowser } from "@/components/topic-browser";
import { mockTopics } from "@/lib/mock/topics";

export const metadata: Metadata = {
  title: "Browse topics",
  description: "Find a debate topic and get matched with someone to argue it.",
};

export default function BrowsePage() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-12 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">Browse topics</h1>
        <p className="mt-1 text-muted-foreground">
          Pick a topic to join the queue, or search for something specific.
        </p>
      </header>

      <TopicBrowser topics={mockTopics} />
    </div>
  );
}
