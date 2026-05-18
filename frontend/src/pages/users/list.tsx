import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { KeyRound, Plus, ShieldOff, UserCheck } from "lucide-react";

import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  FormField,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TR,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { usersApi, type Role, type UserItem } from "@/lib/api/index";
import { useAuth } from "@/lib/auth";

const ROLE_LABEL: Record<Role, string> = {
  admin: "Administrador",
  manager: "Gestor",
  viewer: "Consulta",
};

export function UsersListPage() {
  const { user: currentUser } = useAuth();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [resetTarget, setResetTarget] = useState<UserItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => usersApi.list(),
  });

  const updateRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: Role }) => usersApi.update(id, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const disable = useMutation({
    mutationFn: (id: number) => usersApi.disable(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  const enable = useMutation({
    mutationFn: (id: number) => usersApi.update(id, { status: "active" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });

  if (currentUser && currentUser.role !== "admin") {
    return (
      <div className="mx-auto max-w-3xl p-8">
        <h1 className="text-2xl font-semibold text-brand-700">Usuarios</h1>
        <p className="mt-2 text-sm text-status-expired">
          Solo los administradores pueden gestionar usuarios.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl p-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-brand-700">Usuarios</h1>
          <p className="text-sm text-neutral-600">
            Administra el equipo con acceso a esta organización.
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={16} />
          Nuevo usuario
        </Button>
      </header>

      {isLoading && <p className="text-sm text-neutral-500">Cargando…</p>}

      {data && data.items.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-300 bg-white p-10 text-center">
          <p className="text-sm text-neutral-600">No hay usuarios registrados.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <Table>
          <THead>
            <TR>
              <TH>Nombre</TH>
              <TH>Correo</TH>
              <TH>Rol</TH>
              <TH>Estado</TH>
              <TH>Último acceso</TH>
              <TH className="text-right">Acciones</TH>
            </TR>
          </THead>
          <TBody>
            {data.items.map((u) => (
              <TR key={u.id}>
                <TD className="font-medium text-brand-700">{u.display_name}</TD>
                <TD className="text-neutral-600">{u.email}</TD>
                <TD>
                  <select
                    className="h-8 rounded-md border border-neutral-300 bg-white px-2 text-sm"
                    value={u.role}
                    disabled={u.id === currentUser?.id || updateRole.isPending}
                    onChange={(e) => updateRole.mutate({ id: u.id, role: e.target.value as Role })}
                  >
                    <option value="admin">{ROLE_LABEL.admin}</option>
                    <option value="manager">{ROLE_LABEL.manager}</option>
                    <option value="viewer">{ROLE_LABEL.viewer}</option>
                  </select>
                </TD>
                <TD>
                  <Badge tone={u.status === "active" ? "valid" : "missing"}>
                    {u.status === "active" ? "Activo" : "Deshabilitado"}
                  </Badge>
                </TD>
                <TD className="text-sm text-neutral-500">
                  {u.last_login_at ? new Date(u.last_login_at).toLocaleString("es-MX") : "—"}
                </TD>
                <TD className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="ghost" onClick={() => setResetTarget(u)}>
                      <KeyRound size={14} />
                      Contraseña
                    </Button>
                    {u.status === "active" ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={u.id === currentUser?.id || disable.isPending}
                        onClick={() => disable.mutate(u.id)}
                      >
                        <ShieldOff size={14} />
                        Deshabilitar
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={enable.isPending}
                        onClick={() => enable.mutate(u.id)}
                      >
                        <UserCheck size={14} />
                        Habilitar
                      </Button>
                    )}
                  </div>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}

      {showCreate && <CreateUserDialog onClose={() => setShowCreate(false)} />}
      {resetTarget && (
        <ResetPasswordDialog user={resetTarget} onClose={() => setResetTarget(null)} />
      )}
    </div>
  );
}

function CreateUserDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => {
      const body: import("@/lib/api/index").UserCreate = {
        email: email.trim(),
        display_name: displayName.trim(),
        role,
      };
      if (password) body.password = password;
      return usersApi.create(body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: (e: unknown) => {
      if (e instanceof ApiError && e.code === "email_exists") {
        setError("Ya existe un usuario con ese correo.");
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Error inesperado");
      }
    },
  });

  const canSubmit = email.trim().length > 0 && displayName.trim().length > 0;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Nuevo usuario</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <FormField
            label="Correo"
            type="email"
            placeholder="usuario@empresa.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <FormField
            label="Nombre"
            placeholder="Nombre y apellido"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
          />
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-brand-700">Rol</label>
            <select
              className="h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm"
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
            >
              <option value="admin">{ROLE_LABEL.admin}</option>
              <option value="manager">{ROLE_LABEL.manager}</option>
              <option value="viewer">{ROLE_LABEL.viewer}</option>
            </select>
          </div>
          <FormField
            label="Contraseña (opcional)"
            type="password"
            placeholder="Dejar vacío para solo OAuth"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            hint="Si no se define, el usuario deberá iniciar sesión con OAuth."
          />
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={!canSubmit || create.isPending} onClick={() => create.mutate()}>
              {create.isPending ? "Creando…" : "Crear"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function ResetPasswordDialog({ user, onClose }: { user: UserItem; onClose: () => void }) {
  const qc = useQueryClient();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const reset = useMutation({
    mutationFn: () => usersApi.update(user.id, { password }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: (e: unknown) => {
      setError(e instanceof ApiError ? e.message : "Error inesperado");
    },
  });

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-brand-900/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Cambiar contraseña</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <p className="text-sm text-neutral-600">
            Asignar una nueva contraseña para <span className="font-medium">{user.email}</span>.
          </p>
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">{error}</p>
          )}
          <FormField
            label="Nueva contraseña"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              disabled={password.length < 8 || reset.isPending}
              onClick={() => reset.mutate()}
            >
              {reset.isPending ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
