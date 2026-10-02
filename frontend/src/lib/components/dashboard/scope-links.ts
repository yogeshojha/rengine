import { getContext, setContext } from 'svelte';
import { ROUTES } from '$lib/config/routes';
import { SURFACE, SURFACE_ORDER, type SurfaceDimension } from '$lib/config/surface';
import type { TargetScope } from '$lib/utilities/surface-scope';

const KEY = Symbol('dashboard-scope-links');

export interface ScopeLinks {
	readonly clause: string;
	readonly scope: TargetScope;
}

export function provideScopeLinks(links: ScopeLinks) {
	setContext(KEY, links);
}

export function onDashboard(): boolean {
	return getContext<ScopeLinks | undefined>(KEY) !== undefined;
}

export function scopeClause(values: string[]): string {
	if (!values.length) return '';
	const list = values.map(quoteValue);
	return list.length === 1 ? `target=${list[0]}` : `target=[${list.join(',')}]`;
}

export function withClause(clause: string, q: string): string {
	if (!clause) return q;
	return q.trim() ? `${clause} and (${q})` : clause;
}

function quoteValue(v: string): string {
	return /[\s,()"]/.test(v) ? `"${v.replace(/"/g, '\\"')}"` : v;
}

const PARAM_BY_TAB = new Map<string, string>(SURFACE_ORDER.map((s) => [s.tab, s.queryParam]));

export function useScopedRoutes() {
	const links = getContext<ScopeLinks | undefined>(KEY);
	const surface = (tab: string, query?: Record<string, string>) => {
		const clause = links?.clause ?? '';
		const param = PARAM_BY_TAB.get(tab);
		if (!clause || !param) return ROUTES.surface(tab, query);
		return ROUTES.surface(tab, { ...query, [param]: withClause(clause, query?.[param] ?? '') });
	};
	const results = (tab: string, scanId?: string | null, query?: Record<string, string>) =>
		scanId ? ROUTES.results(tab, scanId, query) : surface(tab, query);
	const rows = (key: SurfaceDimension, q: string) => {
		const spec = SURFACE[key];
		return surface(spec.tab, { ...spec.rowView, [spec.queryParam]: q });
	};
	return {
		surface,
		results,
		rows,
		query: (q: string) => withClause(links?.clause ?? '', q),
		get scope(): TargetScope {
			return links?.scope ?? {};
		}
	};
}
