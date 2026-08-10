import { Card, CardContent, CardHeader } from "@/components/ui/card";

/** Placeholder matching TopicCard's shape, so the grid doesn't reflow when data lands. */
export function TopicCardSkeleton() {
  return (
    <Card aria-hidden>
      <CardHeader className="gap-2">
        <div className="h-4 w-20 animate-pulse rounded bg-muted" />
        <div className="h-5 w-full animate-pulse rounded bg-muted" />
        <div className="h-5 w-2/3 animate-pulse rounded bg-muted" />
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="h-3 w-full animate-pulse rounded bg-muted" />
        <div className="h-3 w-4/5 animate-pulse rounded bg-muted" />
        <div className="mt-4 h-9 w-full animate-pulse rounded bg-muted" />
      </CardContent>
    </Card>
  );
}
