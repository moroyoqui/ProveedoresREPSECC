import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/lib/auth";
import { LoginPage } from "@/pages/auth/login";
import { SupplierDetailPage } from "@/pages/suppliers/detail";
import { SuppliersListPage } from "@/pages/suppliers/list";
import { NewSupplierPage } from "@/pages/suppliers/new";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={<Navigate to="/suppliers" replace />} />
          <Route path="suppliers" element={<SuppliersListPage />} />
          <Route path="suppliers/new" element={<NewSupplierPage />} />
          <Route path="suppliers/:id" element={<SupplierDetailPage />} />
          <Route path="documents" element={<Placeholder title="Documentos" />} />
          <Route path="settings" element={<Placeholder title="Configuración" />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  // Auth state is hydrated by AppShell via /auth/me on mount; if /me returns
  // 401, the apiFetch wrapper throws and the page surfaces. For v1 simplicity,
  // we don't pre-block here.
  useAuth();
  return <>{children}</>;
}

function Placeholder({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold text-brand-700">{title}</h1>
      <p className="mt-2 text-sm text-neutral-600">Próximamente.</p>
    </div>
  );
}
