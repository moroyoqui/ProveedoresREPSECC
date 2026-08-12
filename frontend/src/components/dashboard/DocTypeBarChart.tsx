/** Barras horizontales apiladas de cumplimiento por tipo de documento
 * (spec 005, US1). Layout horizontal: los nombres (largos) van en el eje Y y
 * se leen de corrido sin encimarse; la altura crece con el nº de tipos. */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DocTypeBar } from "@/lib/api/dashboard";
import { STATUS_META, STATUS_ORDER } from "./statusMeta";

type Props = {
  data: DocTypeBar[];
  onBarClick?: (documentTypeId: number) => void;
};

const ROW_HEIGHT = 30;
const Y_AXIS_WIDTH = 190;

function truncate(name: string): string {
  return name.length > 28 ? `${name.slice(0, 27)}…` : name;
}

export function DocTypeBarChart({ data, onBarClick }: Props) {
  const height = Math.max(220, data.length * ROW_HEIGHT + 64);
  // Marca los tipos inactivos en la etiqueta del eje (FR-014, T039).
  const chartData = data.map((d) => ({
    ...d,
    name: d.inactive ? `${d.name} (inactivo)` : d.name,
  }));

  function handleClick(_entry: unknown, index: number) {
    const bar = data[index];
    if (bar) onBarClick?.(bar.document_type_id);
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        layout="vertical"
        data={chartData}
        role="img"
        aria-label="Cumplimiento por tipo de documento"
        margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
        barCategoryGap="20%"
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="name"
          width={Y_AXIS_WIDTH}
          interval={0}
          tick={{ fontSize: 11 }}
          tickFormatter={truncate}
        />
        <Tooltip />
        <Legend />
        {STATUS_ORDER.map((status) => (
          <Bar
            key={status}
            dataKey={status}
            name={STATUS_META[status].label}
            stackId="s"
            fill={STATUS_META[status].color}
            cursor={onBarClick ? "pointer" : "default"}
            onClick={onBarClick ? handleClick : undefined}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
