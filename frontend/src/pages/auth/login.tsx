import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, Card, CardBody, CardHeader, CardTitle, FormField } from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch("/auth/login", {
        method: "POST",
        json: { email, password, audience: "backoffice" },
      });
      navigate("/suppliers", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === "invalid_credentials") {
          setError("Correo o contraseña incorrectos.");
        } else if (err.code === "ambiguous_user") {
          setError("El correo está en más de una organización. Contacta a tu admin.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Error inesperado.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-full items-center justify-center bg-brand-50">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <p className="text-xs uppercase tracking-widest text-brand-500">REPSE</p>
          <CardTitle>Cumplimiento de proveedores</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <form className="space-y-3" onSubmit={handleSubmit}>
            <FormField
              label="Correo"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="admin@repsecc.mx"
            />
            <FormField
              label="Contraseña"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-status-expired">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Entrando…" : "Entrar"}
            </Button>
          </form>

          <p className="text-center text-xs text-neutral-500">
            ¿Eres proveedor?{" "}
            <a href="/portal/login" className="font-medium text-brand-700 hover:underline">
              Entra por el portal
            </a>
          </p>
        </CardBody>
      </Card>
    </main>
  );
}
