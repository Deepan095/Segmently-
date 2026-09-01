import { PageWrapper } from '../components/layout/PageWrapper';
import { JobTable } from '../components/admin/JobTable';

export function AdminJobsPage() {
  return (
    <PageWrapper>
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-1 text-2xl font-bold text-gray-900">Jobs</h1>
        <p className="mb-6 text-sm text-gray-500">
          Monitor the processing pipeline and retry failures.
        </p>
        <JobTable />
      </div>
    </PageWrapper>
  );
}
