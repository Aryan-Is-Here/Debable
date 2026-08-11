"use client";

import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertCircle, Search, SearchX } from "lucide-react";

import { ALL_CATEGORIES, TOPIC_CATEGORIES } from "@/lib/constants/categories";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { TopicCard } from "@/components/topic-card";
import { TopicCardSkeleton } from "@/components/topic-card-skeleton";
import { listTopics, topicKeys, type ListTopicsParams } from "@/services/topics";

const PAGE_SIZE = 12;
const SEARCH_DEBOUNCE_MS = 300;
/** How often to refresh the live "N waiting" counts while Browse is open. */
const WAITING_COUNT_REFRESH_MS = 10_000;

/**
 * Interactive topic browser.
 *
 * Search and category filtering happen **server-side** — the list is paginated, so
 * filtering only the current page would silently hide matches further down.
 */
export function TopicBrowser() {
  const [category, setCategory] = useState<string>(ALL_CATEGORIES);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [page, setPage] = useState(0);

  // Debounced so typing doesn't fire a request per keystroke. The page reset lives in the
  // timeout callback rather than an effect body — a new search invalidates the offset, but
  // setting state synchronously in an effect triggers a cascading render.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query.trim());
      setPage(0);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  function selectCategory(next: string) {
    setCategory(next);
    setPage(0);
  }

  const params: ListTopicsParams = {
    search: debouncedQuery || undefined,
    category: category === ALL_CATEGORIES ? undefined : category,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const { data, isPending, isError, error, isFetching, refetch } = useQuery({
    queryKey: topicKeys.list(params),
    queryFn: ({ signal }) => listTopics(params, { signal }),
    // Keeps the previous page visible while the next one loads, instead of flashing empty.
    placeholderData: keepPreviousData,
    // Overrides the app-wide 30s staleTime: the "N waiting" badge changes as people join
    // and leave queues, and the moment you most want it current is when you switch back to
    // this window — which is exactly when the shared defaults would have served a cached
    // count instead.
    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchInterval: WAITING_COUNT_REFRESH_MS,
  });

  const categories = [ALL_CATEGORIES, ...TOPIC_CATEGORIES];
  const topics = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasMore = (page + 1) * PAGE_SIZE < total;

  return (
    <div className="space-y-6">
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

      <div className="flex flex-wrap gap-2">
        {categories.map((c) => (
          <Button
            key={c}
            variant={c === category ? "default" : "outline"}
            size="sm"
            onClick={() => selectCategory(c)}
            aria-pressed={c === category}
          >
            {c}
          </Button>
        ))}
      </div>

      {isError ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-destructive/50 py-16 text-center">
          <AlertCircle className="size-8 text-destructive" />
          <div>
            <p className="font-medium">Couldn&apos;t load topics</p>
            <p className="text-sm text-muted-foreground">
              {error instanceof Error ? error.message : "Something went wrong."}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Try again
          </Button>
        </div>
      ) : isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <TopicCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <>
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {total} {total === 1 ? "topic" : "topics"}
            {isFetching ? " · updating…" : ""}
          </p>

          {topics.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {topics.map((topic) => (
                <TopicCard key={topic.id} topic={topic} />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border py-16 text-center">
              <SearchX className="size-8 text-muted-foreground" />
              <div>
                <p className="font-medium">No topics found</p>
                <p className="text-sm text-muted-foreground">
                  {debouncedQuery || category !== ALL_CATEGORIES
                    ? "Try a different category or search term."
                    : "Be the first to create one."}
                </p>
              </div>
            </div>
          )}

          {(page > 0 || hasMore) && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page + 1} of {Math.max(1, Math.ceil(total / PAGE_SIZE))}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
