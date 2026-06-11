import { useQuery } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { ApiError } from "@/lib/api";
import { authApi } from "@/lib/api/index";
import { useAuth } from "@/lib/auth";
import { LoginPage } from "@/pages/auth/login";
import { CatalogsHub } from "@/pages/settings/catalogs/index";
import { DocumentTypesPage } from "@/pages/settings/catalogs/document-types";
import { GirosPage } from "@/pages/settings/catalogs/giros";
import { OrganizationSettingsPage } from "@/pages/settings/catalogs/organization";
import { SectorsPage } from "@/pages/settings/catalogs/sectors";
import { SupplierTypeDetailPage } from "@/pages/settings/catalogs/supplier-type-detail";
import { SupplierTypesPage } from "@/pages/settings/catalogs/supplier-types";
import { DashboardPage } from "@/pages/dashboard/index";
import { SupplierDetailPage } from "@/pages/suppliers/detail";
import { EditSupplierPage } from "@/pages/suppliers/edit";
import { SuppliersListPage } from "@/pages/suppliers/list";
import { NewSupplierPage } from "@/pages/suppliers/new";
import { DocumentsListPage } from "@/pages/documents/list";
import { UsersListPage } from "@/pages/users/list";
import { PortalPage } from "@/pages/portal/index";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={<RootRedirect />} />
          <Route path="portal" element={<PortalPage />} />
          <Route path="suppliers" element={<RequireNonSupplier><SuppliersListPage /></RequireNonSupplier>} />
          <Route path="suppliers/new" element={<RequireNonSupplier><NewSupplierPage /></RequireNonSupplier>} />
          <Route path="suppliers/:id" element={<RequireNonSupplier><SupplierDetailPage /></RequireNonSupplier>} />
          <Route path="suppliers/:id/edit" element={<RequireNonSupplier><EditSupplierPage /></RequireNonSupplier>} />
          <Route path="documents" element={<RequireNonSupplier><DocumentsListPage /></RequireNonSupplier>} />
          <Route path="dashboard" element={<RequireNonSupplier><DashboardPage /></RequireNonSupplier>} />
          <Route path="users" element={<RequireNonSupplier><UsersListPage /></RequireNonSupplier>} />
          <Route path="settings" element={<Navigate to="/settings/catalogs/organization" replace />} />
          <Route path="settings/catalogs" element={<RequireNonSupplier><CatalogsHub /></RequireNonSupplier>}>
            <Route path="organization" element={<OrganizationSettingsPage />} />
            <Route path="document-types" element={<DocumentTypesPage />} />
            <Route path="supplier-types" element={<SupplierTypesPage />} />
            <Route path="supplier-types/:id" element={<SupplierTypeDetailPage />} />
            <Route path="sectors" element={<SectorsPage />} />
            <Route path="giros" element={<GirosPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

function RootRedirect() {
  const { user } = useAuth();
  return <Navigate to={user?.role === "supplier" ? "/portal" : "/suppliers"} replace />;
}

function RequireNonSupplier({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (user?.role === "supplier") {
    return <Navigate to="/portal" replace />;
  }
  return <>{children}</>;
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
        supplierId: me.supplier_id,
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
