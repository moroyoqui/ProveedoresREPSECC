/** Dropdown de selección múltiple (spec 005, US3).
 * Usa <details> para la apertura/cierre nativo (accesible, sin click-fuera). */
export type Option = { value: string; label: string };

type Props = {
  label: string;
  options: Option[];
  selected: string[];
  onChange: (next: string[]) => void;
  search?: { value: string; onChange: (v: string) => void; placeholder?: string };
  emptyHint?: string;
};

export function MultiCheckDropdown({
  label,
  options,
  selected,
  onChange,
  search,
  emptyHint,
}: Props) {
  function toggle(value: string) {
    onChange(
      selected.includes(value)
        ? selected.filter((v) => v !== value)
        : [...selected, value]
    );
  }

  const count = selected.length;

  return (
    <details className="relative">
      <summary className="flex h-9 cursor-pointer list-none items-center gap-1 rounded-md border border-neutral-300 bg-white px-3 text-sm text-neutral-700 marker:content-none hover:border-brand-400">
        {label}
        {count > 0 && (
          <span className="ml-1 rounded-full bg-brand-100 px-1.5 text-xs font-semibold text-brand-700">
            {count}
          </span>
        )}
        <span className="ml-1 text-neutral-400">▾</span>
      </summary>
      <div className="absolute z-10 mt-1 max-h-72 w-64 overflow-auto rounded-md border border-neutral-200 bg-white p-2 shadow-lg">
        {search && (
          <input
            type="search"
            value={search.value}
            onChange={(e) => search.onChange(e.target.value)}
            placeholder={search.placeholder ?? "Buscar…"}
            className="mb-2 h-8 w-full rounded border border-neutral-300 px-2 text-sm focus:border-brand-400 focus:outline-none"
          />
        )}
        {options.length === 0 ? (
          <p className="px-1 py-2 text-xs text-neutral-400">
            {emptyHint ?? "Sin opciones"}
          </p>
        ) : (
          options.map((opt) => (
            <label
              key={opt.value}
              className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-neutral-50"
            >
              <input
                type="checkbox"
                checked={selected.includes(opt.value)}
                onChange={() => toggle(opt.value)}
              />
              <span className="truncate">{opt.label}</span>
            </label>
          ))
        )}
      </div>
    </details>
  );
}
