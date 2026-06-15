/**
 * API del portal del proveedor — requiere rol supplier.
 */

import { apiFetch } from "@/lib/api";
import type { ComplianceGrid } from "@/lib/api/index";
import type { DocumentListPage } from "@/lib/api/documents";

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

export type UploadOut = {
  id: number;
  document_type_id: number;
  coverage_period_start: string | null;
  coverage_period_end: string | null;
  status: string;
  file_name_original: string;
  file_size_bytes: number;
  version: number;
  created_at: string;
};

export type SubmissionOut = {
  submission_id: number;
  supplier_id: number;
  document_type_id: number;
  coverage_period_start: string | null;
  submitted_at: string;
  status: "pending" | "approved" | "rejected";
};

export type SubmissionDetail = {
  submission_id: number;
  status: "pending" | "approved" | "rejected";
  submitted_at: string;
  rejection_reason: string | null;
  rejected_at: string | null;
};

export const portalApi = {
  getCompliance: (year?: number): Promise<ComplianceGrid> =>
    apiFetch<ComplianceGrid>(
      `/portal/compliance${year != null ? `?year=${year}` : ""}`
    ),

  getDocumentHistory: (documentTypeId: number): Promise<DocumentHistoryItem[]> =>
    apiFetch<DocumentHistoryItem[]>(`/portal/history/${documentTypeId}`),

  // Lista de archivos de la propia empresa para una celda (spec 013, FR-010).
  listDocuments: (
    documentTypeId: number,
    coveragePeriodStart: string | null,
    limit = 50,
  ): Promise<DocumentListPage> => {
    const params = new URLSearchParams({
      document_type_id: String(documentTypeId),
      limit: String(limit),
    });
    if (coveragePeriodStart != null) params.set("coverage_period_start", coveragePeriodStart);
    return apiFetch<DocumentListPage>(`/portal/documents?${params.toString()}`);
  },

  downloadToken: (documentId: number): Promise<{ token: string; expires_at: string }> =>
    apiFetch<{ token: string; expires_at: string }>(
      `/portal/documents/${documentId}/download-token`
    ),

  upload: (
    file: File,
    documentTypeId: number,
    coveragePeriodStart?: string,
  ): Promise<UploadOut> => {
    const form = new FormData();
    const dotIdx = file.name.lastIndexOf(".");
    const base = dotIdx !== -1 ? file.name.slice(0, dotIdx) : file.name;
    const ext = dotIdx !== -1 ? file.name.slice(dotIdx) : "";
    const renamedFile = new File([file], `${base}_${crypto.randomUUID()}${ext}`, { type: file.type });
    form.append("file", renamedFile);
    form.append("document_type_id", String(documentTypeId));
    if (coveragePeriodStart != null) {
      form.append("coverage_period_start", coveragePeriodStart);
    }
    return apiFetch<UploadOut>("/portal/upload", { method: "POST", body: form });
  },

  submit: (
    documentTypeId: number,
    coveragePeriodStart: string | null,
  ): Promise<SubmissionOut> =>
    apiFetch<SubmissionOut>(`/portal/submit/${documentTypeId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ coverage_period_start: coveragePeriodStart }),
    }),

  getSubmission: (
    documentTypeId: number,
    coveragePeriodStart?: string,
  ): Promise<SubmissionDetail | null> => {
    const qs = coveragePeriodStart
      ? `?coverage_period_start=${encodeURIComponent(coveragePeriodStart)}`
      : "";
    return apiFetch<SubmissionDetail | null>(`/portal/submission/${documentTypeId}${qs}`);
  },
};
