import React from "react";
import { cn } from "@/lib/utils";

export interface FloatingStatBadgeProps {
  value: string | number;
  label: string;
  trend?: string;
  variant?: "charcoal" | "sage" | "amber" | "critical";
  className?: string;
}

export const FloatingStatBadge: React.FC<FloatingStatBadgeProps> = ({
  value,
  label,
  trend,
  variant = "charcoal",
  className,
}) => {
  const variantStyles = {
    charcoal: "bg-charcoal/90 border-sage-300/20 text-white",
    sage: "bg-sage-900/90 border-sage-300/30 text-cream",
    amber: "bg-amber-900/90 border-amber-light/30 text-white",
    critical: "bg-critical-900/90 border-critical-light/40 text-white",
  }[variant];

  return (
    <div
      className={cn(
        "badge-floating-stat select-none",
        variantStyles,
        className
      )}
    >
      <span className="font-serif font-semibold text-base sm:text-lg tracking-tight text-white leading-none">
        {value}
      </span>
      <span className="font-sans text-xs text-cream/80 font-normal whitespace-nowrap">
        {label}
      </span>
      {trend && (
        <span className="text-[10px] font-sans font-medium text-amber-light ml-0.5">
          {trend}
        </span>
      )}
    </div>
  );
};
