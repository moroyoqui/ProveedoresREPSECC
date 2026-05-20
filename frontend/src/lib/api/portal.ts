/**
 * API del portal del proveedor — solo lectura, requiere rol supplier.
 */

import { apiFetch } from "@/lib/api";
import type { ComplianceGrid } from "@/lib/api/index";

export type DocumentHistoryItem = {
  id: number;
  version: number;
  is_latest: boolean;
  coverage_period_start: string | null;
  coverage_period_end: string | null;
  due_date_effective: string | null;
  status: string | null;
  file_name_original: string;
  uploaded_by: number;
  created_at: string | null;
};

export const portalApi = {
  getCompliance: (year?: number): Promise<ComplianceGrid> =>
    apiFetch<ComplianceGrid>(
      `/portal/compliance${year != null ? `?year=${year}` : ""}`
    ),

  getDocumentHistory: (documentTypeId: number): Promise<DocumentHistoryItem[]> =>
    apiFetch<DocumentHistoryItem[]>(`/portal/history/${documentTypeId}`),
};
