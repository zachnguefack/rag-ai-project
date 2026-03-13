import { FormEvent, useState } from 'react';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { adminApi } from '../lib/api/admin';

export function RbacPage() {
  const [data, setData] = useState<any>(null);
  const [role, setRole] = useState('');
  const [permission, setPermission] = useState('');

  const load = async () => {
    const [roles, permissions, matrix] = await Promise.all([adminApi.roles(), adminApi.permissions(), adminApi.rbacMatrix()]);
    setData({ roles, permissions, matrix });
  };

  const validate = async (e: FormEvent) => {
    e.preventDefault();
    const result = await adminApi.validatePermission({ role, permission });
    setData((prev: any) => ({ ...prev, validate: result }));
  };

  return (
    <>
      <PageHeader title="RBAC" subtitle="Roles, permissions, matrix and validation" />
      <div className="card"><button onClick={load}>Load RBAC Data</button><form className="inline-form" onSubmit={validate}><input placeholder="role" value={role} onChange={(e) => setRole(e.target.value)} /><input placeholder="permission" value={permission} onChange={(e) => setPermission(e.target.value)} /><button>Validate</button></form></div>
      <JsonPanel data={data} />
    </>
  );
}
