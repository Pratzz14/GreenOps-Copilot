import { useQuery } from '@tanstack/react-query';

async function getGold<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch('/api/v1' + path, { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.message ?? `Gold request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function useGold<T>(path: string, enabled = true) {
  return useQuery({
    queryKey: ['gold', path],
    queryFn: ({ signal }) => getGold<T>(path, signal),
    enabled,
  });
}
