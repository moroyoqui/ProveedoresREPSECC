import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "./cn";

type Variant = "ghost" | "secondary";

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: ReactNode;
  label: string;
  variant?: Variant;
};

const variants: Record<Variant, string> = {
  ghost: "text-brand-700 hover:bg-brand-50",
  secondary: "bg-white text-brand-700 border border-brand-200 hover:bg-brand-50",
};

export function IconButton({
  icon,
  label,
  variant = "ghost",
  className,
  ...props
}: IconButtonProps) {
  return (
    <div className="relative inline-flex group">
      <button
        type="button"
        aria-label={label}
        className={cn(
          "inline-flex items-center justify-center h-8 w-8 rounded-md transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400",
          "disabled:opacity-50 disabled:pointer-events-none",
          variants[variant],
          className
        )}
        {...props}
      >
        {icon}
      </button>
      <span
        role="tooltip"
        className={cn(
          "absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2 py-1",
          "text-xs text-white bg-neutral-800 rounded whitespace-nowrap",
          "invisible opacity-0 group-hover:visible group-hover:opacity-100",
          "transition-opacity duration-150 pointer-events-none z-50"
        )}
      >
        {label}
      </span>
    </div>
  );
}
