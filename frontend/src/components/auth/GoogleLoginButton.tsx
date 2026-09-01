import { motion } from 'framer-motion';
import { googleLoginUrl } from '../../services/authService';

interface GoogleLoginButtonProps {
  label?: string;
}

/**
 * Anchor (full page navigation, not fetch) that starts the backend Google
 * OAuth redirect flow.
 */
export function GoogleLoginButton({ label = 'Continue with Google' }: GoogleLoginButtonProps) {
  return (
    <motion.a
      href={googleLoginUrl()}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      className="flex w-full items-center justify-center gap-3 rounded-full border-2 border-gray-200 bg-white px-6 py-3 font-semibold text-gray-700 transition-colors hover:border-gray-300 hover:shadow-md"
    >
      <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
        <path
          fill="#4285F4"
          d="M23.06 12.25c0-.85-.08-1.67-.22-2.45H12v4.63h6.2a5.3 5.3 0 0 1-2.3 3.48v2.9h3.72c2.18-2 3.44-4.96 3.44-8.56Z"
        />
        <path
          fill="#34A853"
          d="M12 24c3.11 0 5.72-1.03 7.62-2.79l-3.72-2.9c-1.03.69-2.35 1.1-3.9 1.1-3 0-5.55-2.03-6.46-4.76H1.7v2.99A11.5 11.5 0 0 0 12 24Z"
        />
        <path
          fill="#FBBC05"
          d="M5.54 14.65a6.9 6.9 0 0 1 0-4.3V7.36H1.7a11.5 11.5 0 0 0 0 10.28l3.84-2.99Z"
        />
        <path
          fill="#EA4335"
          d="M12 4.75c1.69 0 3.21.58 4.4 1.72l3.3-3.3C17.72 1.2 15.11 0 12 0A11.5 11.5 0 0 0 1.7 6.36l3.84 2.99C6.45 6.78 9 4.75 12 4.75Z"
        />
      </svg>
      {label}
    </motion.a>
  );
}
