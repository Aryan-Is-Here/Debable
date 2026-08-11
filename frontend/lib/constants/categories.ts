/**
 * The allowed topic categories.
 *
 * Mirrors `backend/app/core/categories.py` — **change both together.** The backend rejects
 * any value outside its own copy, so drift here shows up as a 422 on Create.
 *
 * Deliberately a static list rather than something derived from existing topics: deriving
 * it means an empty database offers no categories, which would make the first topic
 * impossible to create.
 */
export const TOPIC_CATEGORIES = [
  "Technology",
  "Science",
  "Politics",
  "Economics",
  "Society",
  "Ethics",
  "Health",
  "Environment",
  "Education",
  "Culture",
] as const;

export type TopicCategory = (typeof TOPIC_CATEGORIES)[number];

/** Sentinel used by the Browse filter to mean "don't filter". */
export const ALL_CATEGORIES = "All" as const;
