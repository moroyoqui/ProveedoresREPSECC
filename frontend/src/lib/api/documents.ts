/**
 * Typed queries + mutations for the global documents list (US2 Addendum spec 001).
 * Wraps GET /api/v1/documents with cursor pagination and per-filter caching.
 */

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { DocumentOut } from "@/lib/api/index";

// ---------- Types ----------

export type DocumentMiniSupplier = {
  id: number;
  legal_name: string;
};

/** DocumentOut extended with the supplier field returned by the list endpoint. */
export type DocumentListItem = DocumentOut & {
  supplier: DocumentMiniSupplier | null;
};

export type DocumentListFilters = {
  supplier_id?: number;
  document_type_id?: number;
  coverage_period_start?: string;
  status?: "valid" | "expiring_soon" | "expired";
  verified?: boolean;
  q?: string;
  is_latest?: boolean;
  limit?: number;
};

export type DocumentListPage = {
  items: DocumentListItem[];
  next_cursor: string | null;
  has_more: boolean;
};

// ---------- API call ----------

function buildDocumentsUrl(filters: DocumentListFilters): string {
  const qs = new URLSearchParams();
  if (filters.supplier_id != null) qs.set("supplier_id", String(filters.supplier_id));
  if (filters.document_type_id != null)
    qs.set("document_type_id", String(filters.document_type_id));
  if (filters.coverage_period_start) qs.set("coverage_period_start", filters.coverage_period_start);
  if (filters.status) qs.set("status", filters.status);
  if (filters.verified != null) qs.set("verified", String(filters.verified));
  if (filters.q) qs.set("q", filters.q);
  if (filters.is_latest != null) qs.set("is_latest", String(filters.is_latest));
  if (filters.limit != null) qs.set("limit", String(filters.limit));
  const tail = qs.toString();
  return `/documents${tail ? `?${tail}` : ""}`;
}

export function fetchDocumentsList(filters: DocumentListFilters): Promise<DocumentListPage> {
  return apiFetch<DocumentListPage>(buildDocumentsUrl(filters)).then((data) => {
    console.debug("[documents-list] raw response supplier[0]:", data?.items?.[0]?.supplier);
    return data;
  });
}

// ---------- Hook ----------

export function useDocumentsList(filters: DocumentListFilters) {
  return useQuery({
    queryKey: ["documents-list", filters],
    queryFn: () => fetchDocumentsList(filters),
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });
}

/** Spec 017: validar una celda marca como validado su documento vigente. */
export async function validateDocumentType(
  supplierId: number,
  documentTypeId: number,
  coveragePeriodStart: string | null,
  note?: string | null,
): Promise<{ status: string; validated_at: string | null; document_id: number }> {
  return apiFetch<{ status: string; validated_at: string | null; document_id: number }>(
    `/suppliers/${supplierId}/compliance/validate`,
    {
      method: "POST",
      json: {
        document_type_id: documentTypeId,
        coverage_period_start: coveragePeriodStart,
        note: note ?? null,
      },
    }
  );
}

/** Spec 017: retira la validación de la celda. Antes no había forma de deshacerla. */
export async function unvalidateDocumentType(
  supplierId: number,
  documentTypeId: number,
  coveragePeriodStart: string | null,
): Promise<{ status: string; document_id: number }> {
  return apiFetch<{ status: string; document_id: number }>(
    `/suppliers/${supplierId}/compliance/unvalidate`,
    {
      method: "POST",
      json: {
        document_type_id: documentTypeId,
        coverage_period_start: coveragePeriodStart,
      },
    }
  );
}
