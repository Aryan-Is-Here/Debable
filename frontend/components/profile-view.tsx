"use client";

import { useQuery } from "@tanstack/react-query";
import { SignInButton, useAuth } from "@clerk/nextjs";
import { AlertCircle, CalendarDays, Loader2, MessagesSquare, Star } from "lucide-react";

import { AUTH_STALLED_HINT, useAuthReady } from "@/hooks/use-auth-ready";
import { initials } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { TopicCard } from "@/components/topic-card";
import { getProfile, ratingKeys } from "@/services/ratings";
import { listTopics, topicKeys } from "@/services/topics";

const dateFormatter = new Intl.DateTimeFormat("en", { month: "short", year: "numeric" });
const historyDateFormatter = new Intl.DateTimeFormat("en", { month: "short", day: "numeric" });

/**
 * Profile: real debate count, real average rating, real history.
 *
 * Topics come from `GET /topics?mine=true` rather than being embedded in the profile
 * response, so there is one topic query with one set of filtering and paging rules rather
 * than a second, subtly different copy of it.
 */
export function ProfileView() {
  const { getToken } = useAuth();
  const { isLoaded, isSignedIn, signedIn, stalled } = useAuthReady();

  const profile = useQuery({
    queryKey: ratingKeys.profile,
    queryFn: async () => getProfile(await getToken()),
    enabled: signedIn,
  });

  const topics = useQuery({
    queryKey: topicKeys.list({ mine: 1, limit: 50 }),
    queryFn: async () => listTopics({ mine: 1, limit: 50 }, { token: await getToken() }),
    enabled: signedIn,
  });

  if (stalled) {
    return (
      <Centered>
        <AlertCircle className="size-8 text-destructive" />
        <p className="font-medium">Sign-in isn&apos;t loading</p>
        <p className="text-sm text-muted-foreground">{AUTH_STALLED_HINT}</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Reload
        </Button>
      </Centered>
    );
  }

  if (isLoaded && !isSignedIn) {
    return (
      <Centered>
        <p className="font-medium">Sign in to see your profile</p>
        <SignInButton mode="modal">
          <Button>Sign in</Button>
        </SignInButton>
      </Centered>
    );
  }

  if (profile.isError) {
    return (
      <Centered>
        <AlertCircle className="size-8 text-destructive" />
        <p className="font-medium">Couldn&apos;t load your profile</p>
        <Button variant="outline" onClick={() => profile.refetch()}>
          Try again
        </Button>
      </Centered>
    );
  }

  if (!profile.data) {
    return (
      <Centered>
        <Loader2 className="size-8 animate-spin text-primary" />
      </Centered>
    );
  }

  const data = profile.data;
  const createdTopics = topics.data?.items ?? [];

  const stats = [
    { icon: MessagesSquare, label: "Debates", value: String(data.debatesCount) },
    {
      icon: Star,
      label: "Avg rating",
      // An em dash, not a zero. `averageRating` is null until somebody has rated you, and a
      // 0 would read as "rated terribly" rather than "not yet rated".
      value: data.averageRating !== null ? data.averageRating.toFixed(1) : "—",
    },
    {
      icon: CalendarDays,
      label: "Joined",
      value: dateFormatter.format(new Date(data.joinedAt)),
    },
  ] as const;

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-12 sm:px-6">
      <header className="flex items-center gap-4">
        <Avatar className="size-16">
          {data.user.avatarUrl && <AvatarImage src={data.user.avatarUrl} alt="" />}
          <AvatarFallback className="text-xl">{initials(data.user.username)}</AvatarFallback>
        </Avatar>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{data.user.username}</h1>
          <p className="text-sm text-muted-foreground">
            Debater since {dateFormatter.format(new Date(data.joinedAt))}
          </p>
        </div>
      </header>

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

      <section className="mt-10">
        <h2 className="text-lg font-medium">Topics created</h2>
        {createdTopics.length > 0 ? (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {createdTopics.map((topic) => (
              <TopicCard key={topic.id} topic={topic} />
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">No topics created yet.</p>
        )}
      </section>

      <section className="mt-10">
        <h2 className="text-lg font-medium">Recent debates</h2>
        {data.history.length > 0 ? (
          <Card className="mt-4">
            <CardContent className="divide-y divide-border p-0">
              {data.history.map((entry) => (
                <div key={entry.id} className="flex items-center gap-3 px-4 py-3">
                  <Avatar className="size-8">
                    {entry.opponent.avatarUrl && (
                      <AvatarImage src={entry.opponent.avatarUrl} alt="" />
                    )}
                    <AvatarFallback className="text-xs">
                      {initials(entry.opponent.username)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{entry.topicTitle}</p>
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
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">
            No finished debates yet. A debate appears here once it ends.
          </p>
        )}
      </section>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-lg flex-col items-center justify-center gap-3 px-4 text-center">
      {children}
    </div>
  );
}
