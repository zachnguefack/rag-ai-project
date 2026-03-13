import { FormEvent, useState } from 'react';
import { useParams } from 'react-router-dom';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { adminApi } from '../lib/api/admin';
import { documentsApi } from '../lib/api/documents';

export function DocumentDetailPage() {
  const { documentId = '' } = useParams();
  const [payload, setPayload] = useState<any>(null);
  const [departmentId, setDepartmentId] = useState('');

  const loadAll = async () => {
    const [detail, metadata, content, acl, access, versions, adminDetail, audit] = await Promise.all([
      documentsApi.detail(documentId), documentsApi.metadata(documentId), documentsApi.content(documentId), documentsApi.acl(documentId), documentsApi.access(documentId), documentsApi.versions(documentId), adminApi.adminDocumentDetail(documentId), adminApi.documentAudit(documentId),
    ]);
    setPayload({ detail, metadata, content, acl, access, versions, adminDetail, audit });
  };

  const reassign = async (e: FormEvent) => { e.preventDefault(); await adminApi.setDocumentDepartment(documentId, departmentId); await loadAll(); };

  return (
    <>
      <PageHeader title={`Document ${documentId}`} />
      <div className="card"><button onClick={loadAll}>Load Detail</button><form onSubmit={reassign} className="inline-form"><input value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} placeholder="new department_id" /><button>Reassign Department</button></form></div>
      <JsonPanel data={payload} />
    </>
  );
}
