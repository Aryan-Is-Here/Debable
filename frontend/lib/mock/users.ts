import type { UserSummary } from "@/lib/types";

/**
 * Mock users for the UI prototype. Avatars are intentionally null so the
 * Avatar component exercises its initials fallback; swap in URLs freely.
 */
export const mockUsers: Record<string, UserSummary> = {
  ava: { id: "u_ava", username: "ava_lin", avatarUrl: null },
  marcus: { id: "u_marcus", username: "marcus.dev", avatarUrl: null },
  priya: { id: "u_priya", username: "priya_k", avatarUrl: null },
  diego: { id: "u_diego", username: "diego.r", avatarUrl: null },
  sofia: { id: "u_sofia", username: "sofia_w", avatarUrl: null },
  kenji: { id: "u_kenji", username: "kenji.t", avatarUrl: null },
};
