import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";

const TABS = [
  { to: "document-types", label: "Tipos de documento" },
  { to: "supplier-types", label: "Tipos de proveedor" },
];

export function CatalogsHub() {
  const { user } = useAuth();
  const location = useLocation();
  const isRoot = location.pathname.endsWith("/catalogs") || location.pathname.endsWith("/catalogs/");

  if (user && user.role !== "admin") {
    return (
      <div className="mx-auto max-w-3xl p-8">
        <h1 className="text-2xl font-semibold text-brand-700">Catálogos</h1>
        <p className="mt-2 text-sm text-neutral-600">
          Solo administradores pueden gestionar el catálogo de la organización.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <header className="mb-4">
        <p className="text-xs uppercase tracking-widest text-neutral-500">Configuración</p>
        <h1 className="text-2xl font-semibold text-brand-700">Catálogos</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Define qué tipos de documento aplican a tu operación y qué tipos de proveedor existen.
        </p>
      </header>

      <div className="mb-6 flex gap-1 border-b border-neutral-200">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "border-brand-700 text-brand-700"
                  : "border-transparent text-neutral-500 hover:text-brand-500"
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      {isRoot ? (
        <div className="text-sm text-neutral-600">
          Selecciona <Link to="document-types" className="text-brand-500 hover:underline">Tipos de documento</Link>{" "}
          o{" "}
          <Link to="supplier-types" className="text-brand-500 hover:underline">Tipos de proveedor</Link>{" "}
          para empezar.
        </div>
      ) : (
        <Outlet />
      )}
    </div>
  );
}
