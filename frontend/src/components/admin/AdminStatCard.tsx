import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

interface AdminStatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  hint?: string;
  className?: string;
}

/**
 * Single metric tile for the admin dashboard grid. Value is pre-formatted by
 * the caller so this component stays presentational.
 */
export function AdminStatCard({
  label,
  value,
  icon: Icon,
  hint,
  className,
}: AdminStatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -4 }}
      transition={{ duration: 0.25 }}
      className={cn(
        'rounded-2xl border border-white/20 bg-white/70 p-5 shadow-xl backdrop-blur-lg',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
          {label}
        </span>
        <span className="rounded-lg bg-purple-100 p-2 text-purple-600">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-2xl font-bold text-gray-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-gray-500">{hint}</p> : null}
    </motion.div>
  );
}
