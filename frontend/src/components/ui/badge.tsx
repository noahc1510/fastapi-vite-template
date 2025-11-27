import * as React from "react"
import { cn } from "@/lib/utils"

const badgeVariants: Record<string, string> = {
  default: "bg-sky-100 text-sky-800",
  success: "bg-emerald-100 text-emerald-800",
  warning: "bg-amber-100 text-amber-800",
  destructive: "bg-rose-100 text-rose-800",
  muted: "bg-slate-100 text-slate-700",
}

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: keyof typeof badgeVariants
}

const Badge = ({ className, variant = "default", ...props }: BadgeProps) => (
  <span
    className={cn(
      "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
      badgeVariants[variant],
      className
    )}
    {...props}
  />
)

export { Badge }
