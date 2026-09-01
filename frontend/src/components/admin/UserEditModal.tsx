import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { GradientButton } from '../ui/GradientButton';
import { useUpdateAdminUser } from '../../hooks/useAdmin';
import type { AdminUser, AdminUserFlag } from '../../types/admin';

interface UserEditModalProps {
  /** User being edited, or `null` when the modal is closed. */
  user: AdminUser | null;
  onClose: () => void;
}

interface FlagState {
  is_active: boolean;
  is_admin: boolean;
  is_verified: boolean;
}

const FLAGS: { key: AdminUserFlag; label: string; description: string }[] = [
  { key: 'is_active', label: 'Active', description: 'User can sign in and use the app.' },
  { key: 'is_admin', label: 'Admin', description: 'Full access to the admin panel.' },
  {
    key: 'is_verified',
    label: 'Verified',
    description: 'Email address has been confirmed.',
  },
];

function toFlagState(user: AdminUser): FlagState {
  return {
    is_active: user.is_active,
    is_admin: user.is_admin,
    is_verified: user.is_verified,
  };
}

export function UserEditModal({ user, onClose }: UserEditModalProps) {
  const mutation = useUpdateAdminUser();
  const [flags, setFlags] = useState<FlagState>(() =>
    user ? toFlagState(user) : { is_active: false, is_admin: false, is_verified: false },
  );

  useEffect(() => {
    if (user) {
      setFlags(toFlagState(user));
      mutation.reset();
    }
    // Re-sync only when a different user is opened.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  if (!user) {
    return null;
  }

  const original = toFlagState(user);
  const isDirty = FLAGS.some(({ key }) => flags[key] !== original[key]);

  const handleSave = () => {
    const payload: Partial<FlagState> = {};
    FLAGS.forEach(({ key }) => {
      if (flags[key] !== original[key]) {
        payload[key] = flags[key];
      }
    });
    mutation.mutate(
      { userId: user.id, payload },
      { onSuccess: () => onClose() },
    );
  };

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 p-4 backdrop-blur-sm"
        onClick={onClose}
        role="presentation"
      >
        <motion.div
          key="panel"
          initial={{ opacity: 0, scale: 0.95, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 12 }}
          transition={{ duration: 0.2 }}
          className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
          onClick={(event) => event.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-label={`Edit ${user.email}`}
        >
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Edit user</h2>
              <p className="mt-0.5 text-sm text-gray-500">{user.email}</p>
            </div>
            <motion.button
              type="button"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={onClose}
              className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </motion.button>
          </div>

          <div className="mt-5 flex flex-col gap-3">
            {FLAGS.map(({ key, label, description }) => (
              <label
                key={key}
                className="flex cursor-pointer items-start justify-between gap-4 rounded-xl border border-gray-200 p-3"
              >
                <span>
                  <span className="block text-sm font-medium text-gray-900">{label}</span>
                  <span className="block text-xs text-gray-500">{description}</span>
                </span>
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 accent-purple-600"
                  checked={flags[key]}
                  onChange={(event) =>
                    setFlags((prev) => ({ ...prev, [key]: event.target.checked }))
                  }
                />
              </label>
            ))}
          </div>

          {mutation.isError ? (
            <p className="mt-3 text-sm text-red-500" role="alert">
              {mutation.error.message}
            </p>
          ) : null}

          <div className="mt-6 flex justify-end gap-3">
            <motion.button
              type="button"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={onClose}
              className="rounded-full px-5 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-100"
            >
              Cancel
            </motion.button>
            <GradientButton
              type="button"
              onClick={handleSave}
              disabled={!isDirty || mutation.isPending}
              aria-busy={mutation.isPending}
            >
              {mutation.isPending ? 'Saving...' : 'Save changes'}
            </GradientButton>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
