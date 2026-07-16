import type { Metadata } from "next";
import { CalendarDays, MessagesSquare, Star } from "lucide-react";

import { mockProfile } from "@/lib/mock/profile";
import { initials } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { TopicCard } from "@/components/topic-card";

export const metadata: Metadata = {
  title: "Profile",
};

const dateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  year: "numeric",
});

const historyDateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
});

export default function ProfilePage() {
  const profile = mockProfile;

  const stats = [
    {
      icon: MessagesSquare,
      label: "Debates",
      value: String(profile.debatesCount),
    },
    {
      icon: Star,
      label: "Avg rating",
      value: profile.averageRating ? profile.averageRating.toFixed(1) : "—",
    },
    {
      icon: CalendarDays,
      label: "Joined",
      value: dateFormatter.format(new Date(profile.joinedAt)),
    },
  ] as const;

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-12 sm:px-6">
      {/* Identity */}
      <header className="flex items-center gap-4">
        <Avatar className="size-16">
          <AvatarFallback className="text-xl">
            {initials(profile.user.username)}
          </AvatarFallback>
        </Avatar>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {profile.user.username}
          </h1>
          <p className="text-sm text-muted-foreground">
            Debater since {dateFormatter.format(new Date(profile.joinedAt))}
          </p>
        </div>
      </header>

      {/* Stats */}
      <div className="mt-8 grid grid-cols-3 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="flex flex-col items-center gap-1 py-4 text-center">
              <stat.icon className="size-5 text-muted-foreground" />
              <span className="text-xl font-semibold">{stat.value}</span>
              <span className="text-xs text-muted-foreground">{stat.label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Created topics */}
      <section className="mt-10">
        <h2 className="text-lg font-medium">Topics created</h2>
        {profile.createdTopics.length > 0 ? (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {profile.createdTopics.map((topic) => (
              <TopicCard key={topic.id} topic={topic} />
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">
            No topics created yet.
          </p>
        )}
      </section>

      {/* Debate history */}
      <section className="mt-10">
        <h2 className="text-lg font-medium">Recent debates</h2>
        <Card className="mt-4">
          <CardContent className="divide-y divide-border p-0">
            {profile.history.map((entry) => (
              <div
                key={entry.id}
                className="flex items-center gap-3 px-4 py-3"
              >
                <Avatar className="size-8">
                  <AvatarFallback className="text-xs">
                    {initials(entry.opponent.username)}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {entry.topicTitle}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    vs {entry.opponent.username} ·{" "}
                    {historyDateFormatter.format(new Date(entry.date))}
                  </p>
                </div>
                {entry.ratingReceived !== null ? (
                  <Badge variant="secondary" className="gap-1">
                    <Star className="size-3 fill-amber-400 text-amber-400" />
                    {entry.ratingReceived}
                  </Badge>
                ) : (
                  <Badge variant="outline">Not rated</Badge>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
