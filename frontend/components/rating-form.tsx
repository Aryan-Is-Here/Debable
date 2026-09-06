"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { Loader2, Star } from "lucide-react";
import { toast } from "sonner";

import type { DebateRoom } from "@/lib/types";
import { cn, initials } from "@/lib/utils";
import { ApiError } from "@/services/api-client";
import { MAX_COMMENT_LENGTH, ratingKeys, submitRating } from "@/services/ratings";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface RatingFormProps {
  room: DebateRoom;
}

/**
 * Post-debate rating: 1–5 stars and an optional comment, persisted to the `ratings` table.
 *
 * Skipping is deliberately allowed. A forced rating produces compliance rather than signal,
 * and the profile's `averageRating` is nullable precisely so "nobody rated this yet" can be
 * represented honestly.
 */
export function RatingForm({ room }: RatingFormProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { getToken } = useAuth();
  const [score, setScore] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { mutate: send, isPending: submitting } = useMutation({
    mutationFn: async () =>
      submitRating(room.id, { score, comment: comment.trim() || undefined }, await getToken()),
    onSuccess: () => {
      // The results screen reads this to show "already rated" on a revisit.
      queryClient.invalidateQueries({ queryKey: ratingKeys.state(room.id) });
      toast.success("Rating submitted", {
        description: `You rated ${room.opponent.username} ${score}/5.`,
      });
      router.push("/");
    },
    onError: (failure) => {
      // A 409 means the debate was already rated, or has not ended. Both are worth saying
      // precisely — "something went wrong" would send someone hunting for a bug.
      if (failure instanceof ApiError && failure.status === 409) {
        setError(failure.message);
        return;
      }
      setError(
        failure instanceof ApiError ? failure.message : "Couldn't submit that. Try again.",
      );
    },
  });

  function handleSubmit() {
    if (score < 1) {
      setError("Please choose a rating.");
      return;
    }
    setError(null);
    send();
  }

  return (
    <Card>
      <CardHeader className="items-center text-center">
        <Avatar className="mx-auto size-16">
          <AvatarFallback className="text-lg">
            {initials(room.opponent.username)}
          </AvatarFallback>
        </Avatar>
        <CardTitle className="mt-2">
          How was your debate with {room.opponent.username}?
        </CardTitle>
        <CardDescription className="text-balance">
          “{room.topic.title}”
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Stars */}
        <Field data-invalid={!!error} className="items-center">
          <div
            className="flex gap-1"
            role="radiogroup"
            aria-label="Rate your opponent from 1 to 5 stars"
          >
            {[1, 2, 3, 4, 5].map((value) => {
              const active = value <= (hovered || score);
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={score === value}
                  aria-label={`${value} star${value > 1 ? "s" : ""}`}
                  onClick={() => setScore(value)}
                  onMouseEnter={() => setHovered(value)}
                  onMouseLeave={() => setHovered(0)}
                  className="rounded-md p-1 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <Star
                    className={cn(
                      "size-8 transition-colors",
                      active
                        ? "fill-amber-400 text-amber-400"
                        : "text-muted-foreground/40",
                    )}
                  />
                </button>
              );
            })}
          </div>
          {error && <FieldError className="text-center">{error}</FieldError>}
        </Field>

        {/* Comment */}
        <Field>
          <FieldLabel htmlFor="comment">Comment (optional)</FieldLabel>
          <Textarea
            id="comment"
            rows={3}
            placeholder="Respectful? Well-argued? Anything future opponents should know?"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={MAX_COMMENT_LENGTH}
          />
          <FieldDescription>
            {comment.length}/{MAX_COMMENT_LENGTH}
          </FieldDescription>
        </Field>

        <div className="flex justify-center gap-3">
          <Button
            variant="ghost"
            onClick={() => router.push("/")}
            disabled={submitting}
          >
            Skip
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting && <Loader2 className="size-4 animate-spin" />}
            Submit rating
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
