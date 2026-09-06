/**
 * The reasons a debate can be reported.
 *
 * Mirrors `backend/app/core/reports.py` — **change both together.** The backend rejects any
 * value outside its own copy, so drift here shows up as a 422 on submit. There is a backend
 * test that files a report in every listed category, so a value added here and forgotten
 * there fails loudly rather than only for the user who picks it.
 *
 * A fixed list rather than free text because nothing reads these individually in the MVP —
 * a category can be counted, a paragraph can only be read by somebody who never will.
 */
export const REPORT_CATEGORIES = [
  "Harassment",
  "Hate speech",
  "Sexual content",
  "Threats",
  "Spam",
  "Other",
] as const;

export type ReportCategory = (typeof REPORT_CATEGORIES)[number];

/** Mirrors `REPORT_DETAIL_MAX_LENGTH` in `backend/app/core/reports.py`. */
export const MAX_REPORT_DETAIL_LENGTH = 500;
