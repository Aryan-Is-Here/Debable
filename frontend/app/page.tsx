import Link from "next/link";
import { ArrowRight, ScanSearch, Sparkles, Video } from "lucide-react";

import { Button } from "@/components/ui/button";
import { TopicCard } from "@/components/topic-card";
import { getTrendingTopics } from "@/lib/mock/topics";

/** How-it-works items shown beneath the hero. */
const steps = [
  {
    icon: ScanSearch,
    title: "Pick a topic",
    body: "Browse debates by topic or create your own. No random small talk.",
  },
  {
    icon: Video,
    title: "Match & debate",
    body: "Get paired one-on-one with someone who wants to argue the other side.",
  },
  {
    icon: Sparkles,
    title: "Fact-check on demand",
    body: "Submit a claim mid-debate and let the AI verify it against trusted sources.",
  },
] as const;

export default function HomePage() {
  const trending = getTrendingTopics();

  return (
    <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
      {/* Hero */}
      <section className="flex flex-col items-center gap-6 py-20 text-center sm:py-28">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1 text-sm text-muted-foreground">
          <Sparkles className="size-3.5" />
          AI-assisted debates
        </span>
        <h1 className="max-w-3xl text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
          Debate strangers on topics that actually matter
        </h1>
        <p className="max-w-2xl text-pretty text-lg text-muted-foreground">
          DebateMatch pairs you with someone on the opposite side of a topic —
          then lets either of you fact-check any claim on demand, mid-conversation.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button render={<Link href="/browse" />} size="lg">
            Browse topics
            <ArrowRight className="size-4" />
          </Button>
          <Button render={<Link href="/create" />} size="lg" variant="outline">
            Create a topic
          </Button>
        </div>
      </section>

      {/* How it works */}
      <section className="grid gap-4 sm:grid-cols-3">
        {steps.map((step) => (
          <div
            key={step.title}
            className="rounded-lg border border-border bg-card p-6"
          >
            <step.icon className="size-6 text-primary" />
            <h3 className="mt-4 font-medium">{step.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{step.body}</p>
          </div>
        ))}
      </section>

      {/* Trending topics */}
      <section className="py-16">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">
              Trending topics
            </h2>
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
          {trending.map((topic) => (
            <TopicCard key={topic.id} topic={topic} />
          ))}
        </div>
      </section>
    </div>
  );
}
