import { useQuery } from "@tanstack/react-query";

import { documentsApi, type HistoryItem } from "@/lib/api/index";

function fmt(iso: string): string {
  return new Date(iso).toLocaleString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function actorLabel(item: HistoryItem): string {
  if (item.actor.type === "system") return "Sistema";
  return item.actor.user.display_name;
}

export function HistoryTab({ documentId }: { documentId: number }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["document-history", documentId],
    queryFn: () => documentsApi.history(documentId),
  });

  if (isLoading) {
    return <p className="text-sm text-neutral-500">Cargando historial…</p>;
  }

  if (isError || !data) {
    return <p className="text-sm text-status-expired">No se pudo cargar el historial.</p>;
  }

  if (data.items.length === 0) {
    return <p className="text-sm text-neutral-500">Sin eventos registrados.</p>;
  }

  return (
    <ol className="relative border-l border-neutral-200 space-y-4 pl-5">
      {data.items.map((item) => {
        const isSystem = item.actor.type === "system";
        return (
          <li key={item.id} className="relative">
            <span
              className={`absolute -left-[1.35rem] mt-1 flex h-3 w-3 items-center justify-center rounded-full ring-2 ring-white ${
                isSystem ? "bg-neutral-300" : "bg-brand-400"
              }`}
              aria-hidden="true"
            />
            <div className="rounded-md border border-neutral-100 bg-neutral-50 px-3 py-2 text-sm">
              <div className="flex items-baseline justify-between gap-2">
                <span
                  className={`font-medium ${isSystem ? "text-neutral-500" : "text-brand-700"}`}
                >
                  {actorLabel(item)}
                </span>
                <time
                  dateTime={item.occurred_at}
                  className="shrink-0 text-xs text-neutral-400"
                >
                  {fmt(item.occurred_at)}
                </time>
              </div>
              <p className="mt-0.5 text-neutral-700">{item.summary}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
