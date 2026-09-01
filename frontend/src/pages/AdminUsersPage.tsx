import { PageWrapper } from '../components/layout/PageWrapper';
import { UserTable } from '../components/admin/UserTable';

export function AdminUsersPage() {
  return (
    <PageWrapper>
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">Users</h1>
        <p className="mb-6 text-sm text-gray-500">
          Search accounts and manage their access flags.
        </p>
        <UserTable />
      </div>
    </PageWrapper>
  );
}
