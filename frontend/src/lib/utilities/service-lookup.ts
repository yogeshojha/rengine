import { servicesApi } from '$lib/api/scan-results';
import { exactToken } from './scan-insights';
import { compileServiceQuery, emptyServiceQuery, type ServiceRead } from './services';

const CACHE_LIMIT = 200;
const PER_ENTITY = 100;

const cache = new Map<string, Promise<ServiceRead[]>>();

export function servicesOn(
	projectId: string,
	scanId: string,
	field: 'host' | 'ip',
	value: string
): Promise<ServiceRead[]> {
	const key = `${scanId}|${field}|${value}`;
	const hit = cache.get(key);
	if (hit) return hit;
	if (cache.size >= CACHE_LIMIT) cache.clear();
	const q = { ...emptyServiceQuery(), search: exactToken(field, value) };
	const pending = servicesApi
		.search(projectId, scanId, compileServiceQuery(q, 'port', 1, 0, PER_ENTITY))
		.then((r) => r.items)
		.catch((e) => {
			cache.delete(key);
			throw e;
		});
	cache.set(key, pending);
	return pending;
}

export function clearServiceLookup() {
	cache.clear();
}
