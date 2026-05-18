import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui";

export function LoginPage() {
  return (
    <main className="flex min-h-full items-center justify-center bg-brand-50">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <p className="text-xs uppercase tracking-widest text-brand-500">REPSE</p>
          <CardTitle>Cumplimiento de proveedores</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <p className="text-sm text-neutral-600">Inicia sesión con tu cuenta corporativa.</p>
          <a
            href="/api/v1/auth/login/google"
            className="block w-full rounded-md border border-brand-200 px-4 py-2.5 text-center text-sm font-medium text-brand-700 hover:bg-brand-50"
          >
            Continuar con Google
          </a>
          <a
            href="/api/v1/auth/login/microsoft"
            className="block w-full rounded-md bg-brand-700 px-4 py-2.5 text-center text-sm font-medium text-white hover:bg-brand-600"
          >
            Continuar con Microsoft
          </a>
        </CardBody>
      </Card>
    </main>
  );
}
