import { useEffect, useMemo, useState } from 'react';
import { AxiosError } from 'axios';
import { motion } from 'framer-motion';
import { Check, Loader2, Pencil, Search, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAdminUsers, useUpdateAdminUser } from '../../hooks/useAdmin';
import type { AdminUser, AdminUserFlag, AdminUserUpdate } from '../../types/admin';
import { UserEditModal } from './UserEditModal';

const FLAG_COLUMNS: { key: AdminUserFlag; label: string }[] = [
  { key: 'is_active', label: 'Active' },
  { key: 'is_admin', label: 'Admin' },
  { key: 'is_verified', label: 'Verified' },
];

function statusOf(error: unknown): number | undefined {
  return error instanceof AxiosError ? error.response?.status : undefined;
}

interface FlagToggleProps {
  on: boolean;
  busy: boolean;
  label: string;
  onToggle: () => void;
}

function FlagToggle({ on, busy, label, onToggle }: FlagToggleProps) {
  return (
    <motion.button
      type="button"
      whileHover={{ scale: busy ? 1 : 1.05 }}
      whileTap={{ scale: busy ? 1 : 0.92 }}
      disabled={busy}
      onClick={onToggle}
      aria-pressed={on}
      aria-label={label}
      className={cn(
        'inline-flex h-6 w-11 items-center rounded-full border transition-colors disabled:opacity-60',
        on ? 'justify-end border-purple-500 bg-purple-500' : 'justify-start border-gray-300 bg-gray-200',
      )}
    >
      <span className="mx-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-white text-purple-600 shadow-sm">
        {busy ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : on ? (
          <Check className="h-3 w-3" />
        ) : (
          <X className="h-3 w-3 text-gray-400" />
        )}
      </span>
    </motion.button>
  );
}

export function UserTable() {
  const [searchInput, setSearchInput] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [pendingCell, setPendingCell] = useState<string | null>(null);

  // Debounce the search box; reset to page 1 on a new query.
  useEffect(() => {
    const handle = window.setTimeout(() => {
      setQuery(searchInput.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  const usersQuery = useAdminUsers(query, page);
  const updateUser = useUpdateAdminUser();

  const rows = useMemo(() => usersQuery.data?.items ?? [], [usersQuery.data]);
  const totalPages = usersQuery.data?.pages ?? 1;
  const forbidden = statusOf(usersQuery.error) === 403;

  const handleToggle = (user: AdminUser, flag: AdminUserFlag) => {
    const cellKey = `${user.id}:${flag}`;
    setPendingCell(cellKey);
    const next = !user[flag];
    const payload: AdminUserUpdate = {};
    if (flag === 'is_active') payload.is_active = next;
    else if (flag === 'is_admin') payload.is_admin = next;
    else payload.is_verified = next;
    updateUser.mutate(
      { userId: user.id, payload },
      { onSettled: () => setPendingCell((current) => (current === cellKey ? null : current)) },
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search by email or name"
            className="w-full rounded-xl border-2 border-gray-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-purple-500"
            aria-label="Search users"
          />
        </div>
        {usersQuery.isFetching ? (
          <Loader2 className="h-4 w-4 animate-spin text-gray-400" aria-hidden />
        ) : null}
      </div>

      {updateUser.isError ? (
        <p className="text-sm text-red-500" role="alert">
          {updateUser.error.message}
        </p>
      ) : null}

      {forbidden ? (
        <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-700">
          You do not have permission to view users.
        </p>
      ) : usersQuery.isError ? (
        <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          <p>Could not load users.</p>
          <button
            type="button"
            onClick={() => void usersQuery.refetch()}
            className="mt-1 font-semibold underline"
          >
            Try again
          </button>
        </div>
      ) : usersQuery.isLoading ? (
        <p className="px-1 py-8 text-center text-sm text-gray-500">Loading users...</p>
      ) : rows.length === 0 ? (
        <p className="px-1 py-8 text-center text-sm text-gray-500">
          {query ? `No users match "${query}".` : 'No users yet.'}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Projects</th>
                <th className="px-4 py-3">Clips</th>
                {FLAG_COLUMNS.map((col) => (
                  <th key={col.key} className="px-4 py-3">
                    {col.label}
                  </th>
                ))}
                <th className="px-4 py-3 text-right">Edit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50/60">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">
                      {user.full_name ?? '--'}
                    </div>
                    <div className="text-xs text-gray-500">{user.email}</div>
                    {user.oauth_provider ? (
                      <div className="mt-0.5 text-xs uppercase tracking-wide text-purple-500">
                        {user.oauth_provider}
                      </div>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{user.projects_count}</td>
                  <td className="px-4 py-3 text-gray-700">{user.clips_count}</td>
                  {FLAG_COLUMNS.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      <FlagToggle
                        on={user[col.key]}
                        busy={pendingCell === `${user.id}:${col.key}`}
                        label={`Toggle ${col.label.toLowerCase()} for ${user.email}`}
                        onToggle={() => handleToggle(user, col.key)}
                      />
                    </td>
                  ))}
                  <td className="px-4 py-3 text-right">
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => setEditing(user)}
                      className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 hover:text-purple-600"
                      aria-label={`Edit ${user.email}`}
                    >
                      <Pencil className="h-4 w-4" />
                    </motion.button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!usersQuery.isError && totalPages > 1 ? (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <motion.button
              type="button"
              whileHover={{ scale: page > 1 ? 1.05 : 1 }}
              whileTap={{ scale: page > 1 ? 0.95 : 1 }}
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="rounded-lg border border-gray-200 px-3 py-1.5 font-medium disabled:opacity-50"
            >
              Previous
            </motion.button>
            <motion.button
              type="button"
              whileHover={{ scale: page < totalPages ? 1.05 : 1 }}
              whileTap={{ scale: page < totalPages ? 0.95 : 1 }}
              disabled={page >= totalPages}
              onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
              className="rounded-lg border border-gray-200 px-3 py-1.5 font-medium disabled:opacity-50"
            >
              Next
            </motion.button>
          </div>
        </div>
      ) : null}

      <UserEditModal user={editing} onClose={() => setEditing(null)} />
    </div>
  );
}
