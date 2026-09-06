/**
 * Report API client.
 *
 * There is no `getReports`, deliberately: nothing in the MVP reads reports back, and a
 * client function for a screen that does not exist would invite one.
 */

import type { ID } from "@/lib/types";
import type { ReportCategory } from "@/lib/constants/reports";
import { apiRequest } from "@/services/api-client";

export interface Report {
  id: ID;
  roomId: ID;
  reporterId: ID;
  reportedUserId: ID;
  category: ReportCategory;
  detail: string | null;
  createdAt: string;
}

export async function submitReport(
  roomId: string,
  input: { category: ReportCategory; detail?: string },
  token: string | null,
): Promise<Report> {
  return apiRequest<Report>(`/rooms/${roomId}/report`, {
    method: "POST",
    body: input,
    token,
  });
}
