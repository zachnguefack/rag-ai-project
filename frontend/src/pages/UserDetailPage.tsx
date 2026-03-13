import { FormEvent, useState } from 'react';
import { useParams } from 'react-router-dom';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { useAsync } from '../hooks/useAsync';
import { adminApi } from '../lib/api/admin';

export function UserDetailPage() {
  const { userId = '' } = useParams();
  const user = useAsync(() => adminApi.userDetail(userId), [userId]);
  const roles = useAsync(() => adminApi.userRoles(userId), [userId]);
  const departments = useAsync(() => adminApi.userDepartments(userId), [userId]);
  const docAccess = useAsync(() => adminApi.userDocAccess(userId), [userId]);
  const scope = useAsync(() => adminApi.userDocumentScope(userId), [userId]);
  const [role, setRole] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [documentId, setDocumentId] = useState('');

  const addRole = async (e: FormEvent) => { e.preventDefault(); await adminApi.addUserRole(userId, role); setRole(''); roles.run(); };
  const addDepartment = async (e: FormEvent) => { e.preventDefault(); await adminApi.addUserDepartment(userId, departmentId); setDepartmentId(''); departments.run(); };
  const addDoc = async (e: FormEvent) => { e.preventDefault(); await adminApi.grantDocAccess(userId, documentId); setDocumentId(''); docAccess.run(); };

  return (
    <>
      <PageHeader title={`User ${userId}`} subtitle="Roles, departments, and document grants" />
      <JsonPanel data={user.data} />
      <section className="grid two-col">
        <div className="card"><h3>Roles</h3><form onSubmit={addRole}><input value={role} onChange={(e) => setRole(e.target.value)} placeholder="role" /><button>Add</button></form><JsonPanel data={roles.data} /></div>
        <div className="card"><h3>Departments</h3><form onSubmit={addDepartment}><input value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} placeholder="department_id" /><button>Add</button></form><JsonPanel data={departments.data} /></div>
        <div className="card"><h3>Document Access</h3><form onSubmit={addDoc}><input value={documentId} onChange={(e) => setDocumentId(e.target.value)} placeholder="document_id" /><button>Grant</button></form><JsonPanel data={docAccess.data} /></div>
        <div className="card"><h3>Effective Scope</h3><JsonPanel data={scope.data} /></div>
      </section>
    </>
  );
}
