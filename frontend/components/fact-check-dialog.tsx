"use client";

import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import { ApiError } from "@/services/api-client";
import { MAX_CLAIM_LENGTH, MIN_CLAIM_LENGTH } from "@/services/fact-check";

interface FactCheckDialogProps {
  /** Called with the validated claim; resolves when the check is done. */
  onSubmitClaim: (claim: string) => Promise<void>;
}

/**
 * Turn a failed request into something honest.
 *
 * The distinction being preserved is the one the whole feature rests on: a refusal is not a
 * verdict. "We could not check this" and "we checked and could not settle it" must never
 * read the same way, or the user learns to treat an outage as evidence.
 */
function describeFailure(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return error.message;
    if (error.status === 409) return "This debate has ended.";
    if (error.status === 503) {
      return "Couldn't check that claim right now — this isn't a verdict on it. Try again shortly.";
    }
    return error.message;
  }
  return "Couldn't reach the fact-check service. Try again shortly.";
}

/**
 * On-demand fact-check entry point (docs/10-ai-fact-check-design.md): the user submits one
 * specific claim, and the verdict arrives in the debate chat for *both* debaters — pushed
 * over the chat socket rather than returned only to whoever asked.
 */
export function FactCheckDialog({ onSubmitClaim }: FactCheckDialogProps) {
  const [open, setOpen] = useState(false);
  const [claim, setClaim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    const trimmed = claim.trim();
    if (trimmed.length < MIN_CLAIM_LENGTH) {
      setError(`Claim must be at least ${MIN_CLAIM_LENGTH} characters.`);
      return;
    }
    if (trimmed.length > MAX_CLAIM_LENGTH) {
      setError(`Claim must be at most ${MAX_CLAIM_LENGTH} characters.`);
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await onSubmitClaim(trimmed);
      setClaim("");
      setOpen(false);
    } catch (failure) {
      // Deliberately keeps the dialog open: the claim is still in the box, so a rate limit
      // or an outage costs the user a retry rather than retyping.
      setError(describeFailure(failure));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="secondary" />}>
        <Sparkles className="size-4" />
        Fact-check
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request a fact-check</DialogTitle>
          <DialogDescription>
            Submit one specific claim. It is checked against trusted sources
            only, and the verdict is posted in the chat for both debaters.
          </DialogDescription>
        </DialogHeader>

        <Field data-invalid={!!error}>
          <FieldLabel htmlFor="claim">Claim</FieldLabel>
          <Textarea
            id="claim"
            rows={3}
            placeholder="e.g. ATMs increased the total number of bank teller jobs."
            value={claim}
            onChange={(e) => setClaim(e.target.value)}
            aria-invalid={!!error}
            maxLength={MAX_CLAIM_LENGTH + 50}
          />
          <FieldDescription>
            One checkable statement works best — not a whole argument.
          </FieldDescription>
          {error && <FieldError>{error}</FieldError>}
        </Field>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting && <Loader2 className="size-4 animate-spin" />}
            {submitting ? "Checking…" : "Submit claim"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
