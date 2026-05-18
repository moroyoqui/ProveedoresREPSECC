import { Link, Outlet, useLocation } from "react-router-dom";
import { Building2, FileStack, LayoutDashboard, LogOut, Settings, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { authApi } from "@/lib/api/index";
import { useAuth } from "@/lib/auth";
import { cn } from "@/components/ui";

type NavItem = {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  adminOnly?: boolean;
};

const NAV: NavItem[] = [
  { to: "/", label: "Tablero", icon: LayoutDashboard },
  { to: "/suppliers", label: "Proveedores", icon: Building2 },
  { to: "/documents", label: "Documentos", icon: FileStack },
  { to: "/users", label: "Usuarios", icon: Users, adminOnly: true },
  { to: "/settings", label: "Configuración", icon: Settings, adminOnly: true },
];

export function AppShell() {
  const { user, setUser } = useAuth();
  const location = useLocation();

  useQuery({
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
    enabled: !user,
  });

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-64 flex-col border-r border-neutral-200 bg-white md:flex">
        <div className="flex h-16 items-center border-b border-neutral-200 px-6">
          <p className="text-xs uppercase tracking-widest text-brand-500">REPSE</p>
        </div>
        {user?.organization && (
          <div className="border-b border-neutral-100 px-6 py-3 text-sm">
            <p className="font-medium text-brand-700">{user.organization.legalName}</p>
            <p className="text-xs text-neutral-500">{user.organization.rfc}</p>
          </div>
        )}
        <nav className="flex-1 p-3">
          {NAV.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => {
            const Icon = item.icon;
            const active = location.pathname.startsWith(item.to) && item.to !== "/" || location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm",
                  active
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-neutral-600 hover:bg-neutral-50"
                )}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-neutral-100 p-3 text-sm">
          {user && (
            <div className="px-3 py-2">
              <p className="font-medium text-brand-700">{user.displayName}</p>
              <p className="text-xs text-neutral-500">{user.email}</p>
            </div>
          )}
          <form action="/api/v1/auth/logout" method="post" className="block">
            <button
              type="submit"
              className="mt-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-50"
            >
              <LogOut size={16} />
              Cerrar sesión
            </button>
          </form>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-neutral-50">
        <Outlet />
      </main>
    </div>
  );
}
