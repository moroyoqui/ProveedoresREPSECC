/** Render tests del tablero (spec 005, T022 US1). */
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { DashboardPage } from "@/pages/dashboard";
import type { DashboardOut } from "@/lib/api/dashboard";

const mockUseDashboard = vi.fn();
vi.mock("@/lib/api/dashboard", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/dashboard")>(
    "@/lib/api/dashboard"
  );
  return { ...actual, useDashboard: (...args: unknown[]) => mockUseDashboard(...args) };
});

// La barra de filtros usa react-query; aquí probamos sólo el render de datos.
vi.mock("@/components/dashboard/DashboardFilters", () => ({
  DashboardFilters: () => null,
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom"
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  );
}

const baseData: DashboardOut = {
  filters: {
    year: 2026,
    supplier_type: [],
    document_type: [],
    supplier: [],
    status: [],
    include_inactive: false,
  },
  pie: [
    { status: "valid", count: 8, percent: 80 },
    { status: "expiring_soon", count: 0, percent: 0 },
    { status: "expired", count: 1, percent: 10 },
    { status: "missing", count: 1, percent: 10 },
  ],
  by_document_type: [
    {
      document_type_id: 3,
      name: "Opinión SAT",
      inactive: false,
      valid: 8,
      expiring_soon: 0,
      expired: 1,
      missing: 1,
      compliance_percent: 80,
    },
  ],
  kpis: {
    global_compliance_percent: 80,
    active_suppliers: 5,
    at_risk_suppliers: 2,
    expiring_30d: 0,
  },
  suppliers: [
    {
      supplier_id: 1,
      legal_name: "ACME SA de CV",
      rfc: "ACM010101AA1",
      supplier_type: "Construcción",
      status: "active",
      compliance_percent: 80,
      expired: 1,
      missing: 1,
    },
  ],
  available_years: [2026, 2025],
  calculated_at: "2026-06-15T09:31:00-06:00",
  empty_reason: null,
};

describe("DashboardPage", () => {
  it("muestra estado de bienvenida cuando no hay proveedores", () => {
    mockUseDashboard.mockReturnValue({ data: { ...baseData, empty_reason: "no_suppliers" }, isLoading: false, isError: false });
    renderPage();
    expect(screen.getByText(/Registra tu primer proveedor/i)).toBeInTheDocument();
  });

  it("renderiza la vista por defecto con KPIs, gráficos y tabla", () => {
    mockUseDashboard.mockReturnValue({ data: baseData, isLoading: false, isError: false });
    renderPage();
    expect(screen.getByText("Desglose por estado")).toBeInTheDocument();
    expect(screen.getByText("Cumplimiento por tipo de documento")).toBeInTheDocument();
    expect(screen.getByText("Resumen por proveedor")).toBeInTheDocument();
    expect(screen.getByText("ACME SA de CV")).toBeInTheDocument();
    expect(screen.getByText(/Última actualización/i)).toBeInTheDocument();
  });

  it("cambiar el año re-consulta con el nuevo parámetro (US2)", () => {
    mockUseDashboard.mockReturnValue({ data: baseData, isLoading: false, isError: false });
    renderPage();

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "2025" } });

    expect(mockUseDashboard).toHaveBeenLastCalledWith({ year: 2025 });
  });

  it("drill-down de KPIs navega al listado correspondiente (US4)", () => {
    mockUseDashboard.mockReturnValue({ data: baseData, isLoading: false, isError: false });
    renderPage();

    fireEvent.click(screen.getByText("En riesgo"));
    expect(mockNavigate).toHaveBeenCalledWith("/suppliers");

    fireEvent.click(screen.getByText("Por vencer (30 d)"));
    expect(mockNavigate).toHaveBeenCalledWith("/documents?status=expiring_soon");
  });
});
