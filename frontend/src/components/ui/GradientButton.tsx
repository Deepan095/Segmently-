import { motion, type HTMLMotionProps } from 'framer-motion';

type GradientButtonProps = HTMLMotionProps<'button'>;

export function GradientButton({ children, ...props }: GradientButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      className="px-6 py-3 rounded-full font-semibold text-white bg-gradient-to-r from-purple-500 to-pink-500 hover:shadow-lg"
      {...props}
    >
      {children}
    </motion.button>
  );
}
