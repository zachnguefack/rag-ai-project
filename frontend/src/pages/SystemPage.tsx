import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { useAsync } from '../hooks/useAsync';
import { systemApi } from '../lib/api/system';

export function SystemPage() {
  const health = useAsync(() => systemApi.health(), []);
  return (
    <>
      <PageHeader title="Health & System" subtitle="Backend availability" />
      <JsonPanel data={{ loading: health.loading, error: health.error, response: health.data }} />
    </>
  );
}
