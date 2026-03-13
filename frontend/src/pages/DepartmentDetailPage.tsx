import { useParams } from 'react-router-dom';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { useAsync } from '../hooks/useAsync';
import { adminApi } from '../lib/api/admin';

export function DepartmentDetailPage() {
  const { departmentId = '' } = useParams();
  const detail = useAsync(() => adminApi.department(departmentId), [departmentId]);
  const users = useAsync(() => adminApi.departmentUsers(departmentId), [departmentId]);
  const documents = useAsync(() => adminApi.departmentDocuments(departmentId), [departmentId]);
  const files = useAsync(() => adminApi.departmentFiles(departmentId), [departmentId]);

  return (
    <>
      <PageHeader title={`Department ${departmentId}`} />
      <section className="grid two-col">
        <div className="card"><h3>Detail</h3><JsonPanel data={detail.data} /></div>
        <div className="card"><h3>Users</h3><JsonPanel data={users.data} /></div>
        <div className="card"><h3>Documents</h3><JsonPanel data={documents.data} /></div>
        <div className="card"><h3>Files</h3><JsonPanel data={files.data} /></div>
      </section>
    </>
  );
}
