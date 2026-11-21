import type { components } from './schema';

type Models = components['schemas'];
export type Catalog = Models['Catalog'];
export type Dataset = Models['Dataset'];
export type Field = Models['DatasetField'];
export type Draft = Models['Draft'];
export type Definition = Models['Definition'];
export type Visual = Models['Visual'];
export type Rule = Models['Filter'];
export type Metric = Models['Metric'];
export type Scope = Models['Scope'];
export type Chart = Models['Chart'];
export type Saved = Models['Saved'];
export type Result = Models['ResultPage'];
export type Lineage = Models['Lineage'];

export const analysisBase = '/api/v1/analysis';

export async function readJson<T>(url: string, method = 'GET', data?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    ...(data === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === 'string' ? detail : detail?.message
      ?? (Array.isArray(detail) ? detail.map(item => item.msg).join(' · ') : null);
    throw new Error(message ?? `Request failed (${response.status})`);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export function analysis<T>(path: string, method?: string, data?: unknown) {
  return readJson<T>(analysisBase + path, method, data);
}
