import React from "react";
import { cn } from "@/lib/utils";
import { CircularIconButton } from "./CircularIconButton";
import { FloatingStatBadge } from "./FloatingStatBadge";

export interface EditorialCardProps extends React.HTMLAttributes<HTMLDivElement> {
  duotone?: "sage" | "amber" | "none";
  statBadge?: {
    value: string | number;
    label: string;
    trend?: string;
  };
  onActionClick?: () => void;
  actionAriaLabel?: string;
  actionIcon?: "arrow" | "asterisk" | "both" | "custom";
}

export const EditorialCard = React.forwardRef<HTMLDivElement, EditorialCardProps>(
  (
    {
      className,
      children,
      duotone = "none",
      statBadge,
      onActionClick,
      actionAriaLabel = "View details",
      actionIcon = "both",
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          "card-editorial relative group rounded-3xl bg-[#272E23] border border-sage-300/15 p-6 text-cream transition-all duration-300",
          duotone === "sage" && "duotone-sage",
          duotone === "amber" && "duotone-amber",
          className
        )}
        {...props}
      >
        {children}

        {onActionClick && (
          <div className="absolute top-5 right-5 z-10">
            <CircularIconButton
              ariaLabel={actionAriaLabel}
              icon={actionIcon}
              onClick={onActionClick}
            />
          </div>
        )}

        {statBadge && (
          <FloatingStatBadge
            value={statBadge.value}
            label={statBadge.label}
            trend={statBadge.trend}
          />
        )}
      </div>
    );
  }
);

EditorialCard.displayName = "EditorialCard";
