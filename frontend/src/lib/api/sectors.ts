import { apiFetch } from "@/lib/api";

export type SectorItem = {
  id: number;
  name: string;
};

export const sectorsApi = {
  list: (): Promise<SectorItem[]> => apiFetch<SectorItem[]>("/sectors"),

  create: (body: { name: string }): Promise<SectorItem> =>
    apiFetch<SectorItem>("/sectors", { method: "POST", json: body }),

  update: (id: number, body: { name: string }): Promise<SectorItem> =>
    apiFetch<SectorItem>(`/sectors/${id}`, { method: "PATCH", json: body }),

  remove: (id: number): Promise<void> =>
    apiFetch<void>(`/sectors/${id}`, { method: "DELETE" }),
};
