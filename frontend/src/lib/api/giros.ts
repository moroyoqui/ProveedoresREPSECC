import { apiFetch } from "@/lib/api";

export type GiroItem = {
  id: number;
  sector_id: number;
  sector_name: string;
  name: string;
};

export const girosApi = {
  list: (sectorId?: number): Promise<GiroItem[]> => {
    const qs = sectorId != null ? `?sector_id=${sectorId}` : "";
    return apiFetch<GiroItem[]>(`/giros${qs}`);
  },

  create: (body: { sector_id: number; name: string }): Promise<GiroItem> =>
    apiFetch<GiroItem>("/giros", { method: "POST", json: body }),

  update: (id: number, body: { sector_id?: number; name?: string }): Promise<GiroItem> =>
    apiFetch<GiroItem>(`/giros/${id}`, { method: "PATCH", json: body }),

  remove: (id: number): Promise<void> =>
    apiFetch<void>(`/giros/${id}`, { method: "DELETE" }),
};
