import { FormEvent, useState } from 'react';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { ragApi } from '../lib/api/rag';

export function RagPage() {
  const [endpoint, setEndpoint] = useState<'query' | 'chat'>('query');
  const [form, setForm] = useState({ question: '', mode: 'balanced', strict_document_scope: false, department_id: '', document_ids: '' });
  const [result, setResult] = useState<any>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const payload: any = { question: form.question, mode: form.mode, strict_document_scope: form.strict_document_scope };
    if (form.department_id) payload.department_id = form.department_id;
    if (form.document_ids) payload.document_ids = form.document_ids.split(',').map((d) => d.trim());
    setResult(endpoint === 'query' ? await ragApi.query(payload) : await ragApi.chatAsk(payload));
  };

  return (
    <>
      <PageHeader title="RAG Tester" subtitle="Fast endpoint validation for answer quality and grounding" />
      <form className="card" onSubmit={submit}>
        <label>Endpoint<select value={endpoint} onChange={(e) => setEndpoint(e.target.value as 'query' | 'chat')}><option value="query">/rag/query</option><option value="chat">/chat/ask</option></select></label>
        <textarea value={form.question} onChange={(e) => setForm({ ...form, question: e.target.value })} placeholder="Ask a question" required />
        <label>Mode<select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}><option value="strict">strict</option><option value="balanced">balanced</option></select></label>
        <label><input type="checkbox" checked={form.strict_document_scope} onChange={(e) => setForm({ ...form, strict_document_scope: e.target.checked })} /> strict_document_scope</label>
        <input placeholder="department_id (optional)" value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })} />
        <input placeholder="document_ids comma separated" value={form.document_ids} onChange={(e) => setForm({ ...form, document_ids: e.target.value })} />
        <button>Submit</button>
      </form>
      {result && <div className="card"><h3>Answer</h3><p>{result.answer}</p><p>Confidence: {result.confidence_score ?? result.confidence?.score ?? 'n/a'}</p><JsonPanel data={result} /></div>}
    </>
  );
}
