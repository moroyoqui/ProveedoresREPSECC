/** Selector de año del tablero (spec 005, US2). Alimentado por
 * `available_years` del endpoint; el cambio se refleja en el URL (FR-008). */
type Props = {
  value: number;
  years: number[];
  onChange: (year: number) => void;
};

export function YearSelect({ value, years, onChange }: Props) {
  // Garantiza que el año seleccionado siempre esté en la lista de opciones.
  const options = years.includes(value) ? years : [value, ...years];

  return (
    <label className="flex items-center gap-2 text-sm text-neutral-600">
      <span>Año</span>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-md border border-neutral-300 bg-white px-2 py-1 text-sm text-neutral-800 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      >
        {options.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>
    </label>
  );
}
