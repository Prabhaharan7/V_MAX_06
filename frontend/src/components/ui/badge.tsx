import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-amber text-white hover:bg-amber-dark",
        secondary:
          "border-sage-600/30 bg-sage-900/60 text-sage-300 hover:bg-sage-900",
        destructive:
          "border-critical/40 bg-critical/15 text-critical-light font-medium",
        outline: "border-sage-300/30 text-cream",
        warning: "border-amber/40 bg-amber/15 text-amber-light font-medium",
        success: "border-sage-300/40 bg-sage-600/30 text-cream font-medium",
        critical: "border-critical/60 bg-critical/20 text-cream font-medium animate-pulse",
        sage: "border-sage-300/30 bg-sage-900 text-sage-300 font-medium",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }

