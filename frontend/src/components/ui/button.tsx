import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-full text-sm font-medium ring-offset-charcoal transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none",
  {
    variants: {
      variant: {
        default: "bg-amber text-white hover:bg-amber-dark active:scale-[0.98]",
        destructive:
          "bg-critical/20 text-cream border border-critical/40 hover:bg-critical/30 active:scale-[0.98]",
        outline:
          "border border-sage-300/25 bg-transparent text-cream hover:bg-sage-900/60 active:scale-[0.98]",
        secondary:
          "bg-sage-900 text-cream border border-sage-600/30 hover:bg-sage-600/40 active:scale-[0.98]",
        ghost: "hover:bg-sage-900/50 hover:text-white text-sage-300",
        link: "text-amber hover:underline underline-offset-4",
        sage: "bg-sage-600 text-white hover:bg-sage-900 active:scale-[0.98]",
        charcoal: "bg-charcoal text-white border border-sage-300/30 hover:bg-sage-900 active:scale-[0.98]",
        oil: "bg-amber text-white hover:bg-amber-dark active:scale-[0.98]",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-8 rounded-full px-3.5 text-xs",
        lg: "h-12 rounded-full px-8 text-base",
        icon: "h-10 w-10 p-0 rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }

