/** Pastel del desglose por estado (spec 005, US1). */
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { DashboardStatus, PieSlice } from "@/lib/api/dashboard";
import { STATUS_META } from "./statusMeta";

type Props = {
  data: PieSlice[];
  onSliceClick?: (status: DashboardStatus) => void;
};

export function StatusPieChart({ data, onSliceClick }: Props) {
  const chartData = data.map((s) => ({
    ...s,
    name: `${STATUS_META[s.status].label} (${s.percent}%)`,
  }));

  function handleClick(entry: unknown) {
    const e = entry as { status?: DashboardStatus; payload?: { status?: DashboardStatus } };
    const status = e?.status ?? e?.payload?.status;
    if (status) onSliceClick?.(status);
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart role="img" aria-label="Desglose de cumplimiento por estado">
        <Pie
          data={chartData}
          dataKey="count"
          nameKey="name"
          innerRadius={55}
          outerRadius={90}
          paddingAngle={1}
          onClick={onSliceClick ? handleClick : undefined}
        >
          {chartData.map((s) => (
            <Cell
              key={s.status}
              fill={STATUS_META[s.status].color}
              cursor={onSliceClick ? "pointer" : "default"}
            />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
