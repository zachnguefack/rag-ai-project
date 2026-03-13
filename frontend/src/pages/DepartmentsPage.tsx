import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { useAsync } from '../hooks/useAsync';
import { adminApi } from '../lib/api/admin';

export function DepartmentsPage() {
  const departments = useAsync(() => adminApi.departments(), []);
  const [form, setForm] = useState({ department_id: '', name: '', description: '' });

  const createDepartment = async (e: FormEvent) => {
    e.preventDefault();
    await adminApi.createDepartment(form);
    setForm({ department_id: '', name: '', description: '' });
    departments.run();
  };

  return (
    <>
      <PageHeader title="Departments" subtitle="Department inventory and details" />
      <div className="card">
        <form onSubmit={createDepartment} className="inline-form">
          <input placeholder="department_id" value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })} required />
          <input placeholder="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <input placeholder="description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <button>Create</button>
        </form>
        <ul>
          {(departments.data || []).map((d: any) => <li key={d.department_id}><Link to={`/departments/${d.department_id}`}>{d.department_id}</Link> — {d.name}</li>)}
        </ul>
      </div>
      <JsonPanel data={departments.data} />
    </>
  );
}
