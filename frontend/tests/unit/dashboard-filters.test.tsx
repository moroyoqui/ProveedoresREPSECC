/** Tests de la barra de filtros del tablero (spec 005, T033 US3). */
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { DashboardFilters } from "@/components/dashboard/DashboardFilters";
import type { DashboardFilters as Filters } from "@/lib/api/dashboard";

vi.mock("@/lib/api/index", () => ({
  supplierTypesApi: {
    list: vi.fn().mockResolvedValue({ items: [{ id: 1, name: "Construcción" }] }),
  },
  documentTypesApi: {
    list: vi.fn().mockResolvedValue({ items: [{ id: 3, name: "Opinión SAT", active: true }] }),
  },
  suppliersApi: {
    list: vi.fn().mockResolvedValue({
      items: [{ id: 9, legal_name: "ACME SA", rfc: "ACM010101AA1" }],
    }),
  },
}));

function renderBar(filters: Filters) {
  const onChange = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <DashboardFilters filters={filters} onChange={onChange} />
    </QueryClientProvider>
  );
  return onChange;
}

describe("DashboardFilters", () => {
  it("alternar un estado llama onChange con el estado seleccionado", () => {
    const onChange = renderBar({ year: 2026 });
    fireEvent.click(screen.getByLabelText("Faltante"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ status: ["missing"] })
    );
  });

  it('"Limpiar filtros" conserva el año y borra el resto (FR-009)', () => {
    const onChange = renderBar({ year: 2025, status: ["expired"], supplier_type: [1] });
    fireEvent.click(screen.getByText("Limpiar filtros"));
    expect(onChange).toHaveBeenCalledWith({ year: 2025 });
  });

  it("sin filtros activos no muestra el botón de limpiar", () => {
    renderBar({ year: 2026 });
    expect(screen.queryByText("Limpiar filtros")).not.toBeInTheDocument();
  });
});
