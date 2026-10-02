import { vulnerabilitiesApi } from '$lib/api/vulnerabilities';
import { ROUTES } from '$lib/config/routes';
import { SURFACE, SurfaceDimension } from '$lib/config/surface';
import type { VulnFilter, VulnSearchResult } from '$lib/utilities/vulns';

const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];

export function findingsFilter(severities: string[], limit: number): VulnFilter {
	return {
		q: null,
		severities,
		states: [],
		protocols: [],
		templates: [],
		tags: [],
		hosts: [],
		scanners: [],
		kev: false,
		cve: false,
		new: false,
		corroborated: false,
		include_info: false,
		include_suppressed: false,
		sort: 'severity',
		order: 'asc',
		limit,
		offset: 0
	};
}

const CACHE_LIMIT = 200;
const cache = new Map<string, Promise<VulnSearchResult>>();

export function findingsOf(
	projectId: string,
	scanId: string,
	severities: string[],
	limit: number,
	version: string
): Promise<VulnSearchResult> {
	const prefix = `${scanId}|${severities.join(',')}|${limit}|`;
	const key = `${prefix}${version}`;
	let hit = cache.get(key);
	if (!hit) {
		for (const k of cache.keys()) if (k.startsWith(prefix)) cache.delete(k);
		if (cache.size >= CACHE_LIMIT) cache.clear();
		hit = vulnerabilitiesApi.search(projectId, scanId, findingsFilter(severities, limit));
		hit.catch(() => cache.delete(key));
		cache.set(key, hit);
	}
	return hit;
}

export function forgetFindings(scanId: string) {
	for (const key of cache.keys()) if (key.startsWith(`${scanId}|`)) cache.delete(key);
}

export function clearFindings() {
	cache.clear();
}

function severityQuery(severities: string[]): string {
	return severities.map((s) => `severity:${s}`).join(' or ');
}

export function findingsHref(scanId: string, severities: string[]): string {
	return ROUTES.results(VULN.tab, scanId, { [VULN.queryParam]: severityQuery(severities) });
}

export function findingHref(scanId: string, id: string): string {
	return ROUTES.results(VULN.tab, scanId, { vuln: id });
}
