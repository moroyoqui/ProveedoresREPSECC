import { useQuery } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { ApiError } from "@/lib/api";
import { authApi } from "@/lib/api/index";
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
  const { user, setUser } = useAuth();
  const location = useLocation();
  const { isLoading, isError, error } = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const me = await authApi.me();
      setUser({
        id: me.id,
        email: me.email,
        displayName: me.display_name,
        role: me.role,
        organization: {
          id: me.organization.id,
          legalName: me.organization.legal_name,
          rfc: me.organization.rfc,
          timezone: me.organization.timezone,
          expiringSoonThresholdDays: me.organization.expiring_soon_threshold_days,
        },
      });
      return me;
    },
    retry: false,
    staleTime: 60_000,
    enabled: !user,
  });

  if (isLoading && !user) {
    return (
      <main className="flex min-h-full items-center justify-center text-sm text-neutral-500">
        Cargando…
      </main>
    );
  }

  if (isError && error instanceof ApiError && error.status === 401) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

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
