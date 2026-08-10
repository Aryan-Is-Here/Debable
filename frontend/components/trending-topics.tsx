import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TopicCard } from "@/components/topic-card";
import { listTopics } from "@/services/topics";

/**
 * Trending topics for the home page.
 *
 * A server component so the grid is in the initial HTML. If the backend is down the
 * section is simply omitted — a dead API should not take the landing page with it.
 */
export async function TrendingTopics() {
  let topics;
  try {
    // Revalidated rather than cached forever: new topics should surface without a redeploy.
    const page = await listTopics({ limit: 4 }, { next: { revalidate: 30 } });
    topics = page.items;
  } catch {
    return null;
  }

  if (topics.length === 0) return null;

  return (
    <section className="py-16">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Trending topics</h2>
          <p className="text-sm text-muted-foreground">
            The debates people are lining up for right now.
          </p>
        </div>
        <Button
          render={<Link href="/browse" />}
          variant="ghost"
          size="sm"
          className="hidden sm:inline-flex"
        >
          View all
          <ArrowRight className="size-4" />
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {topics.map((topic) => (
          <TopicCard key={topic.id} topic={topic} />
        ))}
      </div>
    </section>
  );
}
