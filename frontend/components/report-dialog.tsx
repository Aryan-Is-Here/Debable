"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Flag, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { MAX_REPORT_DETAIL_LENGTH, REPORT_CATEGORIES } from "@/lib/constants/reports";
import type { ReportCategory } from "@/lib/constants/reports";
import { cn } from "@/lib/utils";
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
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { ApiError } from "@/services/api-client";
import { submitReport } from "@/services/reports";

interface ReportDialogProps {
  roomId: string;
  opponentName: string;
}

/**
 * Report the other debater's conduct.
 *
 * Available **during** the debate, not only after it — harassment is reported while it is
 * happening, which is the one rule that deliberately differs from rating.
 *
 * The confirmation says what actually happens: the report is recorded, and nobody reviews it.
 * The MVP has no moderator (handbook §1 puts moderation out of scope), and a message implying
 * a review that will never occur would be worse than saying nothing — it would teach someone
 * being harassed to wait for help that is not coming.
 */
export function ReportDialog({ roomId, opponentName }: ReportDialogProps) {
  const { getToken } = useAuth();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<ReportCategory | null>(null);
  const [detail, setDetail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (category === null) {
      setError("Choose a reason.");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await submitReport(roomId, { category, detail: detail.trim() || undefined }, await getToken());
      toast.success("Report recorded", {
        description: "Thank you. No one reviews reports in this preview.",
      });
      setOpen(false);
      setCategory(null);
      setDetail("");
    } catch (failure) {
      // 409 means they already reported this debate. Saying so is better than a generic
      // failure, which would leave someone wondering whether the first one registered.
      setError(
        failure instanceof ApiError
          ? failure.message
          : "Couldn't send that report. Try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button variant="ghost" size="sm" />}>
        <Flag className="size-4" />
        Report
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Report {opponentName}</DialogTitle>
          <DialogDescription>
            This is recorded against the debate. It does not end the debate or block anyone —
            use End debate if you want to leave.
          </DialogDescription>
        </DialogHeader>

        <Field data-invalid={!!error}>
          <FieldLabel>Reason</FieldLabel>
          <div
            className="flex flex-wrap gap-2"
            role="radiogroup"
            aria-label="Reason for reporting"
          >
            {REPORT_CATEGORIES.map((value) => {
              const selected = category === value;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setCategory(value)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                    selected
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border hover:bg-muted",
                  )}
                >
                  {value}
                </button>
              );
            })}
          </div>
          {error && <FieldError>{error}</FieldError>}
        </Field>

        <Field>
          <FieldLabel htmlFor="report-detail">Anything to add? (optional)</FieldLabel>
          <Textarea
            id="report-detail"
            rows={3}
            value={detail}
            onChange={(event) => setDetail(event.target.value)}
            maxLength={MAX_REPORT_DETAIL_LENGTH}
            placeholder="What happened?"
          />
          <FieldDescription>
            {detail.length}/{MAX_REPORT_DETAIL_LENGTH} · Reports are stored but not reviewed in
            this preview.
          </FieldDescription>
        </Field>

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleSubmit} disabled={submitting}>
            {submitting && <Loader2 className="size-4 animate-spin" />}
            Send report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
