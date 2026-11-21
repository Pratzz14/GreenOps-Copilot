import type { UseQueryResult } from '@tanstack/react-query';
import type { ReactNode } from 'react';

export default function DashboardRequest<T>({ query, label, children }: {
  query: UseQueryResult<T, Error>;
  label: string;
  children: (data: T) => ReactNode;
}) {
  if (query.isError) return (
    <div className="dashboard-request" role="alert">
      <p>{query.error.message}</p>
      <button type="button" onClick={() => void query.refetch()}>Retry {label}</button>
    </div>
  );
  if (query.data === undefined) return <p className="dashboard-request" role="status">Loading {label}…</p>;
  return children(query.data);
}
