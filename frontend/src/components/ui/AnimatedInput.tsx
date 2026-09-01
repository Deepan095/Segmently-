import { motion, type HTMLMotionProps } from 'framer-motion';
import { forwardRef } from 'react';

interface Props extends HTMLMotionProps<'input'> {
  label?: string;
  error?: string;
}

export const AnimatedInput = forwardRef<HTMLInputElement, Props>(
  ({ label, error, ...props }, ref) => (
    <div>
      {label && <label className="block text-sm font-medium mb-1">{label}</label>}
      <motion.input
        ref={ref}
        whileFocus={{ scale: 1.01 }}
        className={`w-full px-4 py-3 rounded-xl border-2 ${
          error ? 'border-red-500' : 'border-gray-200'
        } focus:border-purple-500 outline-none`}
        {...props}
      />
      {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
    </div>
  ),
);

AnimatedInput.displayName = 'AnimatedInput';
