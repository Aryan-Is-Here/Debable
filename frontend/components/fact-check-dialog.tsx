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

/** Claim length bounds — mirrored from the backend contract in later phases. */
const MIN_CLAIM_LENGTH = 10;
const MAX_CLAIM_LENGTH = 300;

interface FactCheckDialogProps {
  /** Called with the validated claim; resolves when the (mock) check is done. */
  onSubmitClaim: (claim: string) => Promise<void>;
}

/**
 * On-demand fact-check entry point (docs/10-ai-fact-check-design.md): the user
 * submits one specific claim; the result arrives in the debate chat. Phase 1
 * resolves against a mock generator instead of the AI service.
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
            Submit one specific claim. The AI verifies it against trusted
            sources and posts the result in the chat for both debaters.
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
