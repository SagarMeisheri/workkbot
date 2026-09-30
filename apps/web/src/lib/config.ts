/**
 * Application environment configuration for Workkbot Web.
 * Provides parameterized endpoints for local dev and Cloud Run production.
 */
export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export const REVIEWER_EMAIL =
  process.env.NEXT_PUBLIC_REVIEWER_EMAIL || "";

export const REVIEWER_PASSWORD =
  process.env.NEXT_PUBLIC_REVIEWER_PASSWORD || "";
