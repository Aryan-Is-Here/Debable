/**
 * Frontend domain view-models for the DebateMatch UI prototype.
 *
 * These types back the mock data used by Phase 1 screens. Persisted fields map
 * to the database design in `docs/04-database-design.md`; a few fields are
 * marked UI-only and exist purely to make the prototype feel realistic. The
 * authoritative schema (and any API contracts) is finalized in later phases —
 * treat these as presentation models, not the source of truth.
 */

export type ID = string;

/** Lifecycle of a debate topic. Provisional — final values land in Phase 3. */
export type TopicStatus = "open" | "active" | "archived";

/** Public-safe user fields shown in the UI (never exposes email). */
export interface UserSummary {
  id: ID;
  username: string;
  /** Remote avatar URL, or null to fall back to initials. */
  avatarUrl: string | null;
}

/** A debate topic as rendered in lists and detail views. */
export interface Topic {
  id: ID;
  title: string;
  description: string;
  status: TopicStatus;
  creator: UserSummary;

  // --- UI-only fields (not part of the DB schema) ---
  /** Human-readable grouping used for filtering/browsing in the prototype. */
  category: string;
  /** Count of people currently waiting to debate this topic. */
  activeDebaters: number;
  /** ISO-8601 creation timestamp. */
  createdAt: string;
}

/** A one-on-one debate session between two users on a topic. */
export interface DebateRoom {
  id: ID;
  topic: Topic;
  /** The two participants. In the prototype, `you` is the local viewer. */
  you: UserSummary;
  opponent: UserSummary;
  /** ISO-8601 timestamp the debate started. */
  startedAt: string;
}

/** Who authored a chat entry. `system` covers fact-check results and notices. */
export type MessageAuthor = "you" | "opponent" | "system";

/** A single text-chat entry within a debate room. */
export interface ChatMessage {
  id: ID;
  author: MessageAuthor;
  content: string;
  /** ISO-8601 timestamp. */
  createdAt: string;
  /** Present when this message is an AI fact-check result. */
  factCheck?: FactCheck;
}

/** Verdict returned by the on-demand AI fact-check. */
export type FactCheckVerdict = "true" | "false" | "misleading" | "unverified";

/** A cited source backing a fact-check verdict. */
export interface FactCheckSource {
  title: string;
  url: string;
}

/** Result of an on-demand fact-check request (see docs/10-ai-fact-check-design.md). */
export interface FactCheck {
  id: ID;
  claim: string;
  verdict: FactCheckVerdict;
  explanation: string;
  sources: FactCheckSource[];
  /** ISO-8601 timestamp. */
  createdAt: string;
}
