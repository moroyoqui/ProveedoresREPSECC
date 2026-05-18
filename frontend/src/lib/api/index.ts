/**
 * Typed queries + mutations for the REPSE API used by US1.
 *
 * The HTTP layer (`apiFetch`) is in `lib/api.ts`. This module wraps it in
 * domain-specific calls used by the pages.
 */

import { apiFetch } from "@/lib/api";

// ---------- Auth + Org ----------

export type Role = "admin" | "manager" | "viewer";

export type MeResponse = {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  organization: {
    id: number;
    legal_name: string;
    rfc: string;
    contact_email: string;
    expiring_soon_threshold_days: number;
    timezone: string;
    status: string;
  };
};

export const authApi = {
  me: () => apiFetch<MeResponse>("/auth/me"),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
};

// ---------- Users (admin only) ----------

export type UserStatus = "active" | "disabled";

export type UserItem = {
  id: number;
  email: string;
  display_name: string;
  role: Role;
  status: UserStatus;
  last_login_at: string | null;
};

export type UserCreate = {
  email: string;
  display_name: string;
  role: Role;
  password?: string;
};

export type UserPatch = {
  display_name?: string;
  role?: Role;
  status?: UserStatus;
  password?: string;
};

export const usersApi = {
  list: () => apiFetch<{ items: UserItem[] }>("/users"),
  create: (body: UserCreate) => apiFetch<UserItem>("/users", { method: "POST", json: body }),
  update: (id: number, body: UserPatch) =>
    apiFetch<UserItem>(`/users/${id}`, { method: "PATCH", json: body }),
  disable: (id: number) => apiFetch<void>(`/users/${id}`, { method: "DELETE" }),
};

// ---------- Supplier Types (read + admin write, spec 003) ----------

export type Periodicity = "monthly" | "bimonthly" | "annual" | "none";

export type SupplierTypeItem = {
  id: number;
  name: string;
  description: string | null;
  origin: "system" | "custom";
  status: "active" | "archived";
  supplier_count: number;
  requirement_count: number;
  updated_at: string;
};

export type RequirementItem = {
  id: number;
  document_type: {
    id: number;
    slug: string;
    name: string;
    periodicity: Periodicity;
    origin: "canonical" | "custom";
    status: "active" | "archived";
  };
  periodicity_override: Periodicity | null;
  periodicity_effective: Periodicity;
  status: "active" | "retired";
  created_at: string;
  updated_at: string;
};

export type SupplierTypeDetail = SupplierTypeItem & {
  requirements?: RequirementItem[];
};

export const supplierTypesApi = {
  list: (status: "active" | "archived" | "all" = "active") =>
    apiFetch<{ items: SupplierTypeItem[] }>(`/supplier-types?status=${status}`),
  detail: (id: number) =>
    apiFetch<SupplierTypeDetail>(`/supplier-types/${id}?include_requirements=true`),
  create: (body: { name: string; description?: string }) =>
    apiFetch<SupplierTypeItem>("/supplier-types", { method: "POST", json: body }),
  update: (id: number, etag: string, body: { name?: string; description?: string }) =>
    apiFetch<SupplierTypeItem>(`/supplier-types/${id}`, { method: "PATCH", etag, json: body }),
  archive: (id: number, reason?: string) =>
    apiFetch<SupplierTypeItem & { affected_suppliers_count: number }>(
      `/supplier-types/${id}/archive`,
      { method: "POST", json: { reason: reason ?? null } }
    ),
  restore: (id: number) =>
    apiFetch<SupplierTypeItem>(`/supplier-types/${id}/restore`, { method: "POST" }),
  delete: (id: number, etag: string) =>
    apiFetch<void>(`/supplier-types/${id}`, { method: "DELETE", etag }),
  addRequirement: (
    id: number,
    body: { document_type_id: number; periodicity_override: Periodicity | null }
  ) =>
    apiFetch<RequirementItem>(`/supplier-types/${id}/requirements`, {
      method: "POST",
      json: body,
    }),
  updateRequirement: (
    reqId: number,
    etag: string,
    body: { periodicity_override: Periodicity | null }
  ) =>
    apiFetch<RequirementItem>(`/supplier-type-requirements/${reqId}`, {
      method: "PATCH",
      etag,
      json: body,
    }),
  retireRequirement: (reqId: number, etag: string) =>
    apiFetch<void>(`/supplier-type-requirements/${reqId}`, { method: "DELETE", etag }),
};

// ---------- Document Types (read + admin write, spec 003) ----------

export type DocumentTypeItem = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  periodicity: Periodicity;
  origin: "canonical" | "custom";
  status: "active" | "archived";
  active: boolean;
  updated_at: string;
};

export const documentTypesApi = {
  list: (includeInactive = false) =>
    apiFetch<{ items: DocumentTypeItem[] }>(
      `/document-types${includeInactive ? "?include_inactive=true" : ""}`
    ),
  create: (body: { name: string; description?: string; periodicity: Periodicity }) =>
    apiFetch<DocumentTypeItem>("/document-types", { method: "POST", json: body }),
  update: (
    id: number,
    etag: string,
    body: { name?: string; description?: string; periodicity?: Periodicity }
  ) =>
    apiFetch<DocumentTypeItem>(`/document-types/${id}`, { method: "PATCH", etag, json: body }),
  toggleCanonical: (id: number, active: boolean, reason?: string) =>
    apiFetch<{ id: number; slug: string; name: string; active: boolean }>(
      `/document-types/${id}/toggle-active`,
      { method: "POST", json: { active, reason: reason ?? null } }
    ),
  archive: (id: number) =>
    apiFetch<DocumentTypeItem>(`/document-types/${id}/archive`, { method: "POST" }),
  restore: (id: number) =>
    apiFetch<DocumentTypeItem>(`/document-types/${id}/restore`, { method: "POST" }),
  delete: (id: number, etag: string) =>
    apiFetch<void>(`/document-types/${id}`, { method: "DELETE", etag }),
};

// ---------- Suppliers ----------

export type SupplierStatus = "active" | "inactive";

export type SupplierListItem = {
  id: number;
  legal_name: string;
  rfc: string;
  supplier_type: { id: number; name: string; origin: string };
  contact_name: string | null;
  contact_email: string | null;
  status: SupplierStatus;
  compliance_percent: number;
  counts: { valid: number; expiring_soon: number; expired: number; missing: number };
  created_at: string;
};

export type SupplierDetail = SupplierListItem & {
  documents_by_type: Array<{
    document_type: { id: number; slug: string; name: string; periodicity: string };
    latest: null | {
      id: number;
      coverage_period_start: string | null;
      coverage_period_end: string | null;
      due_date_effective: string | null;
      status: string;
      verified: boolean;
      uploaded_at: string | null;
    };
    status_override: string | null;
  }>;
};

export type SupplierCreate = {
  legal_name: string;
  rfc: string;
  supplier_type_id?: number;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  notes?: string;
};

export const suppliersApi = {
  list: (params: { q?: string; status?: string; supplier_type_id?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q);
    if (params.status) qs.set("status", params.status);
    if (params.supplier_type_id) qs.set("supplier_type_id", String(params.supplier_type_id));
    const tail = qs.toString();
    return apiFetch<{ items: SupplierListItem[]; has_more: boolean }>(
      `/suppliers${tail ? `?${tail}` : ""}`
    );
  },
  detail: (id: number) => apiFetch<SupplierDetail>(`/suppliers/${id}`),
  create: (body: SupplierCreate) =>
    apiFetch<SupplierListItem>("/suppliers", { method: "POST", json: body }),
};

// ---------- Documents ----------

export type DocumentOut = {
  id: number;
  supplier_id: number;
  document_type_id: number;
  coverage_period_start: string | null;
  coverage_period_end: string | null;
  due_date_calculated: string | null;
  due_date_effective: string | null;
  status: "valid" | "expiring_soon" | "expired";
  verified: boolean;
  version: number;
  is_latest: boolean;
  file: { name: string; size_bytes: number; mime_type: string; sha256: string };
  ocr: {
    status: "not_run" | "pending" | "success" | "failed";
    extracted_rfc: string | null;
    extracted_issued_at: string | null;
    extracted_valid_until: string | null;
  };
  audit: {
    added: { user: { id: number; display_name: string }; at: string };
    last_updated: null | { user: { id: number; display_name: string }; at: string };
    validated: null | { user: { id: number; display_name: string }; at: string; note: string | null };
  };
};

export const documentsApi = {
  upload: async (params: {
    supplier_id: number;
    document_type_id: number;
    coverage_period_start?: string;
    due_date_override?: string;
    due_date_override_reason?: string;
    file: File;
  }): Promise<DocumentOut> => {
    const form = new FormData();
    form.append("file", params.file);
    form.append("document_type_id", String(params.document_type_id));
    if (params.coverage_period_start) form.append("coverage_period_start", params.coverage_period_start);
    if (params.due_date_override) form.append("due_date_override", params.due_date_override);
    if (params.due_date_override_reason) form.append("due_date_override_reason", params.due_date_override_reason);
    return apiFetch<DocumentOut>(
      `/suppliers/${params.supplier_id}/documents`,
      { method: "POST", body: form }
    );
  },
  verify: (id: number, note?: string) =>
    apiFetch<DocumentOut>(`/documents/${id}/verify`, {
      method: "POST",
      json: { note },
    }),
};
