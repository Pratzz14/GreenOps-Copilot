export const dashboardPageSize = 10;

export default function DashboardPagination({ page, total, label, onPage, pageSize = dashboardPageSize }: {
  page: number;
  total: number;
  label: string;
  onPage: (page: number) => void;
  pageSize?: number;
}) {
  if (total <= pageSize) return null;
  const start = page * pageSize;
  const end = Math.min(start + pageSize, total);
  return <div className="pagination" role="group" aria-label={label}>
    <button type="button" disabled={page === 0} onClick={() => onPage(page - 1)}>Previous</button>
    <span aria-live="polite">{start + 1}–{end} of {total}</span>
    <button type="button" disabled={end === total} onClick={() => onPage(page + 1)}>Next</button>
  </div>;
}
