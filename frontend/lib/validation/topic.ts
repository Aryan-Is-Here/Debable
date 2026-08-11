import { z } from "zod";

import { TOPIC_CATEGORIES } from "@/lib/constants/categories";

/**
 * Validation schema for creating a debate topic.
 *
 * Shared, framework-agnostic source of truth for topic input: used by the
 * Create Topic form now, and reusable for API request validation once the
 * backend lands (see `docs/04-database-design.md`). Keep field names aligned
 * with the Topic model.
 */
export const createTopicSchema = z.object({
  title: z
    .string()
    .trim()
    .min(10, "Title must be at least 10 characters.")
    .max(120, "Title must be at most 120 characters."),
  description: z
    .string()
    .trim()
    .min(20, "Description must be at least 20 characters.")
    .max(600, "Description must be at most 600 characters."),
  // Enumerated rather than a free string so the form rejects a bad value before the
  // request is made. The backend enforces the same list — see lib/constants/categories.
  category: z.enum(TOPIC_CATEGORIES, {
    message: "Please choose a category.",
  }),
});

export type CreateTopicInput = z.infer<typeof createTopicSchema>;
