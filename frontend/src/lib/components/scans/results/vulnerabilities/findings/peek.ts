import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
import { compileVulnQuery, emptyVulnQuery, type VulnSearchResult } from '$lib/utilities/vulns';

const CACHE_LIMIT = 200;
const cache = new Map<string, Promise<VulnSearchResult>>();

export function peek(
	projectId: string,
	scanId: string,
	q: string,
	limit: number,
	sort = 'severity'
): Promise<VulnSearchResult> {
	const key = `${projectId}|${scanId}|${q}|${limit}|${sort}`;
	let hit = cache.get(key);
	if (!hit) {
		if (cache.size >= CACHE_LIMIT) cache.clear();
		hit = vulnerabilitiesApi.search(
			projectId,
			scanId,
			compileVulnQuery({ ...emptyVulnQuery(), search: q }, sort, 1, 0, limit)
		);
		hit.catch(() => cache.delete(key));
		cache.set(key, hit);
	}
	return hit;
}

export function forgetPeeks() {
	cache.clear();
}
