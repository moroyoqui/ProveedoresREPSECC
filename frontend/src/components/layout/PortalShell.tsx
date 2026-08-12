import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Eye, LogOut, Upload } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { authApi } from "@/lib/api/index";
import { useAuth } from "@/lib/auth";
import { cn } from "@/components/ui";

const NAV = [
  { to: "/portal/consulta", label: "Consulta", icon: Eye },
  { to: "/portal/carga", label: "Carga de documentos", icon: Upload },
];

/**
 * Layout exclusivo del portal del proveedor (spec 013, FR-014):
 * menú independiente con solo Consulta / Carga / cerrar sesión.
 * Ninguna opción del back-office administrativo es visible aquí.
 */
export function PortalShell() {
  const { user, setUser } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const qc = useQueryClient();

  async function handleLogout() {
    await authApi.logout().catch(() => {});
    setUser(null);
    qc.removeQueries({ queryKey: ["me"] });
    navigate("/portal/login");
  }

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-64 flex-col border-r border-emerald-900/40 bg-emerald-800 md:flex">
        <div className="flex h-16 flex-col justify-center border-b border-white/20 px-6">
          <p className="text-xs uppercase tracking-widest text-emerald-200">REPSE</p>
          <p className="text-sm font-semibold text-white">Portal del Proveedor</p>
        </div>
        {user?.organization && (
          <div className="border-b border-white/20 px-6 py-3 text-sm">
            <p className="font-medium text-white">{user.organization.legalName}</p>
            <p className="text-xs text-emerald-200">{user.organization.rfc}</p>
          </div>
        )}
        <nav className="flex-1 p-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm",
                  active
                    ? "bg-white/20 font-medium text-white"
                    : "text-emerald-100 hover:bg-white/10"
                )}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/20 p-3 text-sm">
          {user && (
            <div className="px-3 py-2">
              <p className="font-medium text-white">{user.displayName}</p>
              <p className="text-xs text-emerald-200">{user.email}</p>
            </div>
          )}
          <button
            type="button"
            onClick={handleLogout}
            className="mt-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-emerald-100 hover:bg-white/10"
          >
            <LogOut size={16} />
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-neutral-50">
        <Outlet />
      </main>
    </div>
  );
}
