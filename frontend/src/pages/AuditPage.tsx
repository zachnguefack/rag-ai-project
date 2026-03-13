import { FormEvent, useState } from 'react';
import { JsonPanel } from '../components/JsonPanel';
import { PageHeader } from '../components/PageHeader';
import { adminApi } from '../lib/api/admin';

export function AuditPage() {
  const [logs, setLogs] = useState<any>(null);
  const [eventId, setEventId] = useState('');

  const load = async () => setLogs(await adminApi.auditLogs());
  const loadEvent = async (e: FormEvent) => {
    e.preventDefault();
    const detail = await adminApi.auditLogDetail(eventId);
    setLogs((prev: any) => ({ ...prev, selected: detail }));
  };

  return (
    <>
      <PageHeader title="Audit Logs" subtitle="Operational event stream" />
      <div className="card"><button onClick={load}>Load Logs</button><form className="inline-form" onSubmit={loadEvent}><input value={eventId} onChange={(e) => setEventId(e.target.value)} placeholder="event_id" /><button>Load Event</button></form></div>
      <JsonPanel data={logs} />
    </>
  );
}
