import { motion } from 'framer-motion';
import { ReactNode } from 'react';

export function AnimatedList({ children }: { children: ReactNode[] }) {
  return (
    <motion.div initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}>
      {children.map((child, i) => (
        <motion.div key={i} variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}>
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}
