import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border",
  {
    variants: {
      variant: {
        default: "bg-slate-100 text-slate-800 border-slate-200",
        critical: "bg-red-100 text-red-700 border-red-200",
        high: "bg-orange-100 text-orange-700 border-orange-200",
        medium: "bg-amber-100 text-amber-700 border-amber-200",
        low: "bg-lime-100 text-lime-700 border-lime-200",
        info: "bg-gray-100 text-gray-600 border-gray-200",
        open: "bg-blue-100 text-blue-700 border-blue-200",
        in_progress: "bg-yellow-100 text-yellow-700 border-yellow-200",
        resolved: "bg-green-100 text-green-700 border-green-200",
        accepted: "bg-purple-100 text-purple-700 border-purple-200",
        suppressed: "bg-slate-100 text-slate-500 border-slate-200",
        active: "bg-green-100 text-green-700 border-green-200",
        error: "bg-red-100 text-red-700 border-red-200",
        pending: "bg-yellow-100 text-yellow-700 border-yellow-200",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
