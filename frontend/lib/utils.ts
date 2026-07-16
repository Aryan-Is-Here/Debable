import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Two-letter uppercase initials from a username, for avatar fallbacks. */
export function initials(username: string): string {
  return username.replace(/[^a-zA-Z]/g, "").slice(0, 2).toUpperCase() || "?"
}
