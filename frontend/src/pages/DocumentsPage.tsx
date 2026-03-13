import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { documentsApi } from '../lib/api/documents';

export function DocumentsPage() {
  const [query, setQuery] = useState('');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => { setLoading(true); setData(await documentsApi.list()); setLoading(false); };
  const search = async (e: FormEvent) => { e.preventDefault(); setLoading(true); setData(query ? await documentsApi.search(query) : await documentsApi.list()); setLoading(false); };
  const triggerIndex = async () => { await documentsApi.index(false); };

  return (
    <>
      <PageHeader title="Documents" subtitle="Searchable document catalog and indexing" />
      <div className="card"><form onSubmit={search} className="inline-form"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="search query" /><button>Search</button><button type="button" onClick={load}>Load</button><button type="button" onClick={triggerIndex}>Trigger Index</button></form></div>
      {loading && <p>Loading...</p>}
      <div className="card">
        <table>
          <thead><tr><th>ID</th><th>Title</th><th>Dept</th><th /></tr></thead>
          <tbody>{(data?.items || []).map((d: any) => <tr key={d.document_id}><td>{d.document_id}</td><td>{d.title}</td><td>{d.department_id}</td><td><Link to={`/documents/${d.document_id}`}>Open</Link></td></tr>)}</tbody>
        </table>
      </div>
      <JsonPanel data={data} />
    </>
  );
}
