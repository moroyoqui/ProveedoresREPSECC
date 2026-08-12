/**
 * Suppliers — type-change destructive flow (T131 spec 001).
 *
 * Provee:
 *  - `useSupplierTypeChangePreview(supplierId, newTypeId)` — query lazy que
 *    consulta `GET /suppliers/{id}/type-change-preview` cuando se conoce el
 *    nuevo tipo.
 *  - `useChangeSupplierType(supplierId)` — mutación que envía el PATCH con
 *    el campo opcional `confirmation_text` y propaga los errores 409 / 422
 *    como ApiError tipados.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationOptions,
} from "@tanstack/react-query";

import { ApiError, apiFetch } from "@/lib/api";
import type { SupplierDetail } from "@/lib/api/index";

export type AffectedDocument = {
  id: number;
  document_type: string;
  coverage_period: string | null;
  due_date_effective: string | null;
};

export type SupplierTypeChangePreview = {
  requires_confirmation: boolean;
  affected_count: number;
  affected_documents: AffectedDocument[];
};

export type SupplierTypeChangeError =
  | { kind: "confirmation_required"; affected_documents: AffectedDocument[]; affected_count: number }
  | { kind: "invalid_confirmation"; expected: string }
  | { kind: "other"; message: string };

export type ChangeSupplierTypeInput = {
  supplier_type_id: number;
  confirmation_text?: string;
};

export function fetchSupplierTypeChangePreview(
  supplierId: number,
  newTypeId: number
): Promise<SupplierTypeChangePreview> {
  return apiFetch<SupplierTypeChangePreview>(
    `/suppliers/${supplierId}/type-change-preview?supplier_type_id=${newTypeId}`
  );
}

export function useSupplierTypeChangePreview(
  supplierId: number,
  newTypeId: number | null
) {
  return useQuery({
    queryKey: ["supplier-type-change-preview", supplierId, newTypeId],
    queryFn: () => fetchSupplierTypeChangePreview(supplierId, newTypeId as number),
    enabled: Number.isFinite(supplierId) && newTypeId != null,
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });
}

export function parseTypeChangeError(error: unknown): SupplierTypeChangeError {
  if (error instanceof ApiError) {
    if (error.code === "confirmation_required") {
      const details = (error.details ?? {}) as Record<string, unknown>;
      return {
        kind: "confirmation_required",
        affected_count: Number(details.affected_count ?? 0),
        affected_documents: (details.affected_documents as AffectedDocument[]) ?? [],
      };
    }
    if (error.code === "invalid_confirmation") {
      const details = (error.details ?? {}) as Record<string, unknown>;
      return {
        kind: "invalid_confirmation",
        expected: String(details.expected ?? "eliminar"),
      };
    }
    return { kind: "other", message: error.message };
  }
  return { kind: "other", message: "Error inesperado" };
}

export function useChangeSupplierType(
  supplierId: number,
  options?: Omit<
    UseMutationOptions<SupplierDetail, unknown, ChangeSupplierTypeInput>,
    "mutationFn"
  >
) {
  const qc = useQueryClient();
  return useMutation<SupplierDetail, unknown, ChangeSupplierTypeInput>({
    mutationFn: (input) =>
      apiFetch<SupplierDetail>(`/suppliers/${supplierId}`, {
        method: "PATCH",
        json: input,
      }),
    onSuccess: (...args) => {
      qc.invalidateQueries({ queryKey: ["supplier", supplierId] });
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      options?.onSuccess?.(...args);
    },
    ...options,
  });
}
