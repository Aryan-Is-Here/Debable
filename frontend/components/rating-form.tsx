"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Star } from "lucide-react";
import { toast } from "sonner";

import type { DebateRoom } from "@/lib/types";
import { cn, initials } from "@/lib/utils";
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

const MAX_COMMENT_LENGTH = 300;

/**
 * Post-debate rating (1–5 stars + optional comment). Mock submit in Phase 1;
 * maps to the Ratings table (docs/04-database-design.md) in later phases.
 */
export function RatingForm({ room }: RatingFormProps) {
  const router = useRouter();
  const [score, setScore] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (score < 1) {
      setError("Please choose a rating.");
      return;
    }
    setError(null);
    setSubmitting(true);
    // Mock submit — persistence arrives with the backend (Phase 8).
    await new Promise((resolve) => setTimeout(resolve, 600));
    toast.success("Rating submitted", {
      description: `You rated ${room.opponent.username} ${score}/5.`,
    });
    router.push("/");
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
