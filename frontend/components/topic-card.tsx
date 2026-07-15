import Link from "next/link";
import { Users } from "lucide-react";

import type { Topic, TopicStatus } from "@/lib/types";
import { initials } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

/** Maps a topic status to a Badge variant. */
const statusVariant: Record<
  TopicStatus,
  React.ComponentProps<typeof Badge>["variant"]
> = {
  active: "default",
  open: "secondary",
  archived: "outline",
};

interface TopicCardProps {
  topic: Topic;
}

/** Presentational card for a single debate topic. Pure/mock-data driven. */
export function TopicCard({ topic }: TopicCardProps) {
  return (
    <Card className="flex h-full flex-col transition-colors hover:border-primary/40">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <Badge variant="outline">{topic.category}</Badge>
          <Badge variant={statusVariant[topic.status]} className="capitalize">
            {topic.status}
          </Badge>
        </div>
        <CardTitle className="mt-2 text-balance leading-snug">
          <Link
            href={{ pathname: "/waiting", query: { topic: topic.id } }}
            className="hover:underline"
          >
            {topic.title}
          </Link>
        </CardTitle>
        <CardDescription className="line-clamp-2">
          {topic.description}
        </CardDescription>
      </CardHeader>

      <CardContent className="mt-auto">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Avatar className="size-6">
            <AvatarFallback className="text-[10px]">
              {initials(topic.creator.username)}
            </AvatarFallback>
          </Avatar>
          <span>{topic.creator.username}</span>
        </div>
      </CardContent>

      <CardFooter className="justify-between text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <Users className="size-4" />
          {topic.activeDebaters} waiting
        </span>
        {topic.status !== "archived" && (
          <Button
            render={
              <Link href={{ pathname: "/waiting", query: { topic: topic.id } }} />
            }
            size="sm"
          >
            Debate
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
