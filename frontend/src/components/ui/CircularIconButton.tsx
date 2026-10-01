import React from "react";
import { ArrowUpRight, Asterisk } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CircularIconButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: "arrow" | "asterisk" | "both" | "custom";
  customIcon?: React.ReactNode;
  ariaLabel?: string;
}

export const CircularIconButton = React.forwardRef<
  HTMLButtonElement,
  CircularIconButtonProps
>(({ className, icon = "both", customIcon, ariaLabel = "View details", ...props }, ref) => {
  return (
    <button
      ref={ref}
      aria-label={ariaLabel}
      title={ariaLabel}
      type="button"
      className={cn(
        "btn-circular-action group shrink-0 relative overflow-hidden select-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:ring-offset-2 focus:ring-offset-charcoal",
        className
      )}
      {...props}
    >
      {icon === "both" && (
        <div className="relative w-5 h-5 flex items-center justify-center">
          <Asterisk className="w-4 h-4 text-charcoal/40 group-hover:opacity-0 group-hover:scale-75 transition-all duration-200" />
          <ArrowUpRight className="w-4 h-4 text-charcoal absolute inset-0 m-auto opacity-0 scale-75 group-hover:opacity-100 group-hover:scale-100 transition-all duration-200 stroke-[2.2]" />
        </div>
      )}
      {icon === "arrow" && (
        <ArrowUpRight className="w-4 h-4 text-charcoal group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-200 stroke-[2.2]" />
      )}
      {icon === "asterisk" && (
        <Asterisk className="w-4 h-4 text-charcoal group-hover:rotate-45 transition-transform duration-200" />
      )}
      {icon === "custom" && customIcon}
    </button>
  );
});

CircularIconButton.displayName = "CircularIconButton";
