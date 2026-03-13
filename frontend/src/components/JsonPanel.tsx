export function JsonPanel({ data }: { data: unknown }) {
  return <pre className="json-panel">{JSON.stringify(data, null, 2)}</pre>;
}
