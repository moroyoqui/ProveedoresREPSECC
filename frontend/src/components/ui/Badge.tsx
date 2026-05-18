import type { HTMLAttributes } from "react";

import { cn } from "./cn";

export type BadgeTone = "neutral" | "valid" | "expiring" | "expired" | "missing" | "info";

const tones: Record<BadgeTone, string> = {
  neutral: "bg-neutral-100 text-neutral-700",
  valid: "bg-emerald-50 text-status-valid",
  expiring: "bg-amber-50 text-status-expiring",
  expired: "bg-red-50 text-status-expired",
  missing: "bg-neutral-100 text-status-missing",
  info: "bg-brand-50 text-brand-700",
};

export function Badge({
  tone = "neutral",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
