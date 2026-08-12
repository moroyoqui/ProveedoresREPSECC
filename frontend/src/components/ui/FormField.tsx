import type { InputHTMLAttributes, ReactNode } from "react";
import { forwardRef, useId } from "react";

import { cn } from "./cn";

export type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
};

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(function FormField(
  { id, label, hint, error, className, ...props },
  ref
) {
  const generated = useId();
  const fieldId = id ?? generated;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={fieldId} className="text-sm font-medium text-brand-700">
        {label}
      </label>
      <input
        id={fieldId}
        ref={ref}
        className={cn(
          "h-10 rounded-md border bg-white px-3 text-sm",
          "border-neutral-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400",
          error ? "border-status-expired focus-visible:ring-red-300" : null,
          className
        )}
        aria-invalid={error ? "true" : undefined}
        {...props}
      />
      {hint && !error && <p className="text-xs text-neutral-500">{hint}</p>}
      {error && <p className="text-xs text-status-expired">{error}</p>}
    </div>
  );
});
