/** Spec 016 (US1): visibilidad y confirmación del botón de borrado. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { DocumentDetailDrawer } from "@/components/documents/DocumentDetailDrawer";
import { AuthProvider } from "@/lib/auth";
import type { DocumentListItem } from "@/lib/api/documents";

const mockRemove = vi.fn();
vi.mock("@/lib/api/index", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/index")>("@/lib/api/index");
  return {
    ...actual,
    documentsApi: {
      ...actual.documentsApi,
      remove: (...args: unknown[]) => mockRemove(...args),
    },
  };
});

// El historial hace su propia petición; no es lo que se prueba aquí.
vi.mock("@/components/documents/HistoryTab", () => ({
  HistoryTab: () => null,
}));

function makeDoc(overrides: Partial<DocumentListItem> = {}): DocumentListItem {
  return {
    id: 42,
    supplier_id: 7,
    supplier: { id: 7, legal_name: "Servicios Industriales del Norte" },
    document_type_id: 3,
    document_type: { id: 3, name: "Opinión SAT", slug: "opinion-sat", periodicity: "monthly" },
    coverage_period_start: "2026-04-01",
    coverage_period_end: "2026-04-30",
    due_date_calculated: "2026-05-17",
    due_date_effective: "2026-05-17",
    status: "valid",
    verified: false,
    version: 1,
    is_latest: true,
    can_delete: true,
    file: { name: "opinion.pdf", size_bytes: 1024, mime_type: "application/pdf", sha256: "abc" },
    ocr: { status: "success", extracted_rfc: null, extracted_issued_at: null, extracted_valid_until: null },
    audit: {
      added: { user: { id: 9, display_name: "Gestor Uno" }, at: "2026-04-02T10:00:00Z" },
      last_updated: null,
      validated: null,
    },
    ...overrides,
  } as DocumentListItem;
}

function renderDrawer(doc: DocumentListItem, onDeleteSuccess = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <DocumentDetailDrawer
          document={doc}
          onClose={vi.fn()}
          onVerify={vi.fn()}
          onUnverifySuccess={vi.fn()}
          onDeleteSuccess={onDeleteSuccess}
        />
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe("botón de borrado del drawer", () => {
  beforeEach(() => {
    mockRemove.mockReset();
  });

  it("se muestra cuando el servidor autoriza el borrado", () => {
    renderDrawer(makeDoc({ can_delete: true }));
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeInTheDocument();
  });

  it("no se muestra cuando el servidor no lo autoriza", () => {
    renderDrawer(makeDoc({ can_delete: false }));
    expect(screen.queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
  });

  it("pide confirmación nombrando el documento antes de borrar", () => {
    renderDrawer(makeDoc());
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    expect(screen.getByRole("heading", { name: "Eliminar documento" })).toBeInTheDocument();
    expect(
      screen.getByText(/Servicios Industriales del Norte · Opinión SAT/)
    ).toBeInTheDocument();
    // Nada se ha borrado todavía.
    expect(mockRemove).not.toHaveBeenCalled();
  });

  it("cancelar cierra el diálogo sin llamar a la API", () => {
    renderDrawer(makeDoc());
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByText("Eliminar documento")).not.toBeInTheDocument();
    expect(mockRemove).not.toHaveBeenCalled();
  });
});
