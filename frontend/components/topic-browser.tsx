"use client";

import { useMemo, useState } from "react";
import { Search, SearchX } from "lucide-react";

import type { Topic } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { TopicCard } from "@/components/topic-card";

const ALL = "All" as const;

interface TopicBrowserProps {
  topics: Topic[];
}

/**
 * Interactive topic browser: filter by category and search title/description.
 * Filtering is client-side over the provided list (mock data in Phase 1).
 */
export function TopicBrowser({ topics }: TopicBrowserProps) {
  const [category, setCategory] = useState<string>(ALL);
  const [query, setQuery] = useState("");

  const categories = useMemo(
    () => [ALL, ...Array.from(new Set(topics.map((t) => t.category))).sort()],
    [topics],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return topics
      .filter((t) => category === ALL || t.category === category)
      .filter(
        (t) =>
          q === "" ||
          t.title.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q),
      )
      .sort((a, b) => b.activeDebaters - a.activeDebaters);
  }, [topics, category, query]);

  return (
    <div className="space-y-6">
      {/* Search */}
      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search topics…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-9"
          aria-label="Search topics"
        />
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        {categories.map((c) => (
          <Button
            key={c}
            variant={c === category ? "default" : "outline"}
            size="sm"
            onClick={() => setCategory(c)}
            aria-pressed={c === category}
          >
            {c}
          </Button>
        ))}
      </div>

      {/* Results */}
      <p className="text-sm text-muted-foreground" aria-live="polite">
        {filtered.length} {filtered.length === 1 ? "topic" : "topics"}
      </p>

      {filtered.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((topic) => (
            <TopicCard key={topic.id} topic={topic} />
          ))}
        </div>
      ) : (
        <div
          className={cn(
            "flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border py-16 text-center",
          )}
        >
          <SearchX className="size-8 text-muted-foreground" />
          <div>
            <p className="font-medium">No topics found</p>
            <p className="text-sm text-muted-foreground">
              Try a different category or search term.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
