export function JsonBlock({ data }: { data: unknown }) {
  return <pre className="json-block">{JSON.stringify(data ?? null, null, 2)}</pre>;
}
