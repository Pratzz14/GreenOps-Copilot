import type { components } from './schema';
export type QualityOverview = components['schemas']['QualityOverview'];
export type SourceDetail = components['schemas']['SourceDetail'];
export type IssuePage = components['schemas']['IssuePage'];
export type Scope = 'full' | 'baseline';
export async function readQuality<T>(path: string, signal?: AbortSignal): Promise<T> {
 const response = await fetch(`/api/v1/data-quality${path}`, {signal});
 if (!response.ok) {const body = await response.json().catch(()=>null) as {detail?:{message?:string}}|null;throw Error(body?.detail?.message??`Analysis request failed (${response.status}).`);}
 return response.json() as Promise<T>;
}
