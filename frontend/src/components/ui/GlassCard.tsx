import { motion } from 'framer-motion';
import { ReactNode } from 'react';

export function GlassCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -5 }}
      className={`p-6 rounded-2xl bg-white/10 backdrop-blur-lg border border-white/20 shadow-xl ${className}`}
    >
      {children}
    </motion.div>
  );
}
