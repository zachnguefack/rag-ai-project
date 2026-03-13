import { Link } from 'react-router-dom';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';
import { PageHeader } from '../components/PageHeader';
import { useAsync } from '../hooks/useAsync';
import { adminApi } from '../lib/api/admin';

export function UsersPage() {
  const users = useAsync(() => adminApi.users(), []);

  return (
    <>
      <PageHeader title="Users Management" subtitle="Available admin user endpoints" />
      {users.loading && <LoadingState />}
      {users.error && <ErrorState message={users.error} />}
      <div className="card">
        <table>
          <thead><tr><th>User ID</th><th>Username</th><th>Email</th><th /></tr></thead>
          <tbody>
            {(users.data?.items || []).map((u: any) => (
              <tr key={u.user_id}><td>{u.user_id}</td><td>{u.username}</td><td>{u.email}</td><td><Link to={`/users/${u.user_id}`}>Open</Link></td></tr>
            ))}
          </tbody>
        </table>
        {!users.loading && (users.data?.items || []).length === 0 && <p>No users returned.</p>}
      </div>
    </>
  );
}
