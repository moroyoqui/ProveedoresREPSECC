import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

export function AppRouter() {
  // Routes are filled in by Phase 3 (US1) and beyond. For Phase 2 this is a
  // placeholder so the frontend boots and renders.
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

function Landing() {
  return (
    <main className="flex min-h-full items-center justify-center bg-brand-50">
      <div className="rounded-xl border border-brand-100 bg-white p-10 text-center shadow-sm">
        <p className="text-sm uppercase tracking-widest text-brand-500">REPSE</p>
        <h1 className="mt-2 text-3xl font-semibold text-brand-700">Cumplimiento de proveedores</h1>
        <p className="mt-4 max-w-sm text-sm text-neutral-600">
          La aplicación está en bootstrap. Phase 3 trae los flujos de US1.
        </p>
      </div>
    </main>
  );
}
