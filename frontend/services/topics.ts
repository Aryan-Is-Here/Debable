/**
 * Topic API client.
 *
 * Returns the same `lib/types.ts` view-models the mock layer returned, so screens did not
 * need rewriting when the backend arrived.
 */

import type { Topic, TopicStatus } from "@/lib/types";
import { apiRequest, type RequestOptions } from "@/services/api-client";

/** Matches the backend's `Page[T]` envelope. */
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ListTopicsParams {
  search?: string;
  category?: string;
  status?: TopicStatus;
  limit?: number;
  offset?: number;
  /** Index signature so these can be passed straight through as query parameters. */
  [key: string]: string | number | undefined;
}

export interface CreateTopicPayload {
  title: string;
  description: string;
  category: string;
}

export async function listTopics(
  params: ListTopicsParams = {},
  options: Pick<RequestOptions, "signal" | "next" | "cache"> = {},
): Promise<Page<Topic>> {
  return apiRequest<Page<Topic>>("/topics", { params, ...options });
}

export async function getTopic(
  id: string,
  options: Pick<RequestOptions, "signal" | "next" | "cache"> = {},
): Promise<Topic> {
  return apiRequest<Topic>(`/topics/${id}`, options);
}

export async function createTopic(
  payload: CreateTopicPayload,
  token: string | null,
): Promise<Topic> {
  return apiRequest<Topic>("/topics", { method: "POST", body: payload, token });
}

/** Query keys, kept in one place so mutations can invalidate precisely. */
export const topicKeys = {
  all: ["topics"] as const,
  list: (params: ListTopicsParams) => ["topics", "list", params] as const,
  detail: (id: string) => ["topics", "detail", id] as const,
};
