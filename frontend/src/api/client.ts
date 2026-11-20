import type { components } from './schema';

type Health = components['schemas']['Health'];

export async function getHealth(): Promise<Health> {
  const response = await fetch('/api/v1/health');
  if (!response.ok) throw new Error(`Health request failed (${response.status})`);
  return response.json() as Promise<Health>;
}
