/** Tabla resumen por proveedor (spec 005, US1). */
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui";
import type { SupplierRow } from "@/lib/api/dashboard";

type Props = {
  rows: SupplierRow[];
};

export function ComplianceSummaryTable({ rows }: Props) {
  return (
    <Table>
      <THead>
        <TR>
          <TH>Proveedor</TH>
          <TH>RFC</TH>
          <TH>Tipo</TH>
          <TH>Cumplimiento</TH>
          <TH>Vencidos</TH>
          <TH>Faltantes</TH>
        </TR>
      </THead>
      <TBody>
        {rows.map((r) => {
          const tone =
            r.compliance_percent >= 80
              ? "text-status-valid"
              : r.compliance_percent >= 50
              ? "text-status-expiring"
              : "text-status-expired";
          return (
            <TR key={r.supplier_id}>
              <TD>{r.legal_name}</TD>
              <TD className="font-mono text-xs">{r.rfc}</TD>
              <TD>{r.supplier_type ?? "Sin clasificar"}</TD>
              <TD className={`font-semibold ${tone}`}>{r.compliance_percent}%</TD>
              <TD>{r.expired}</TD>
              <TD>{r.missing}</TD>
            </TR>
          );
        })}
      </TBody>
    </Table>
  );
}
