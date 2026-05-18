import { useEffect, useId, useRef, useState } from "react";

import { Button } from "./Button";
import { Card, CardBody, CardHeader, CardTitle } from "./Card";
import { cn } from "./cn";

const EXPECTED = "eliminar";

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

export type DestructiveConfirmItem = {
  id: number | string;
  primary: string;
  secondary?: string;
};

export type DestructiveConfirmDialogProps = {
  title: string;
  description: string;
  items: DestructiveConfirmItem[];
  itemsLabel?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * Modal de confirmación destructiva (T130 spec 001).
 *
 * Muestra el conteo y resumen de los elementos a eliminar y obliga al usuario
 * a escribir literalmente "eliminar" (case-insensitive, trim) para habilitar
 * el botón de confirmación. El botón Cancelar está siempre habilitado.
 */
export function DestructiveConfirmDialog({
  title,
  description,
  items,
  itemsLabel = "Documentos a eliminar",
  confirmLabel = "Eliminar y aplicar cambio",
  cancelLabel = "Cancelar",
  busy = false,
  onConfirm,
  onCancel,
}: DestructiveConfirmDialogProps) {
  const inputId = useId();
  const [text, setText] = useState("");
  const cancelRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  const matches = normalize(text) === EXPECTED;
  const confirmDisabled = !matches || busy;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={`${inputId}-title`}
    >
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>
            <span id={`${inputId}-title`}>{title}</span>
          </CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <p className="text-sm text-neutral-700">{description}</p>

          <section className="rounded-md border border-red-200 bg-red-50 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-status-expired">
              {itemsLabel} ({items.length})
            </p>
            <ul className="mt-2 max-h-48 overflow-y-auto text-sm text-neutral-700">
              {items.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-col border-b border-red-100 py-1 last:border-b-0"
                >
                  <span className="font-medium">{item.primary}</span>
                  {item.secondary && (
                    <span className="text-xs text-neutral-500">{item.secondary}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>

          <div>
            <label
              htmlFor={inputId}
              className="text-sm font-medium text-brand-700"
            >
              Escribe <span className="font-mono font-bold">{EXPECTED}</span> para
              confirmar
            </label>
            <input
              id={inputId}
              type="text"
              autoComplete="off"
              spellCheck={false}
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={busy}
              aria-describedby={`${inputId}-hint`}
              className={cn(
                "mt-1.5 h-10 w-full rounded-md border bg-white px-3 text-sm",
                matches
                  ? "border-status-expired focus:border-status-expired focus:outline-none focus:ring-2 focus:ring-red-200"
                  : "border-neutral-300 focus:outline-none focus:ring-2 focus:ring-brand-400"
              )}
            />
            <p id={`${inputId}-hint`} className="mt-1 text-xs text-neutral-500">
              La comparación ignora mayúsculas/minúsculas y espacios al inicio o fin.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-1">
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
              ref={cancelRef}
            >
              {cancelLabel}
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={onConfirm}
              disabled={confirmDisabled}
              aria-disabled={confirmDisabled}
              data-testid="destructive-confirm-button"
            >
              {busy ? "Procesando…" : confirmLabel}
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
