import { PageHeader } from '../components/PageHeader';
import { useAuth } from '../context/AuthContext';
import { useAsync } from '../hooks/useAsync';
import { adminApi } from '../lib/api/admin';
import { documentsApi } from '../lib/api/documents';
import { systemApi } from '../lib/api/system';

export function DashboardPage() {
  const { user } = useAuth();
  const { data: health } = useAsync(() => systemApi.health(), []);
  const { data: departments } = useAsync(() => adminApi.departments(), []);
  const { data: docs } = useAsync(() => documentsApi.list(1, 0), []);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Backend operational summary" />
      <div className="grid cards">
        <article className="card"><h3>Current User</h3><p>{user?.username}</p></article>
        <article className="card"><h3>Departments</h3><p>{departments?.length ?? '-'}</p></article>
        <article className="card"><h3>Visible Documents</h3><p>{docs?.total ?? '-'}</p></article>
        <article className="card"><h3>Health</h3><p>{health?.status ?? 'unknown'}</p></article>
      </div>
    </>
  );
}
