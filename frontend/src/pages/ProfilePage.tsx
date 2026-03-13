import { ErrorState } from '../components/ErrorState';
import { JsonPanel } from '../components/JsonPanel';
import { LoadingState } from '../components/LoadingState';
import { PageHeader } from '../components/PageHeader';
import { useAsync } from '../hooks/useAsync';
import { authApi } from '../lib/api/auth';
import { usersApi } from '../lib/api/users';

export function ProfilePage() {
  const me = useAsync(() => authApi.me(), []);
  const profile = useAsync(() => usersApi.me(), []);
  const permissions = useAsync(() => usersApi.permissions(), []);

  return (
    <>
      <PageHeader title="Current User" subtitle="Auth and effective scope details" />
      {me.loading ? <LoadingState /> : me.error ? <ErrorState message={me.error} /> : <JsonPanel data={me.data} />}
      <h3>/users/me</h3>
      {profile.loading ? <LoadingState /> : profile.error ? <ErrorState message={profile.error} /> : <JsonPanel data={profile.data} />}
      <h3>/users/permissions</h3>
      {permissions.loading ? <LoadingState /> : permissions.error ? <ErrorState message={permissions.error} /> : <JsonPanel data={permissions.data} />}
    </>
  );
}
