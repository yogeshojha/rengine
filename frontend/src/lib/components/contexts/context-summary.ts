import type { ScanContextRead, ScanContextCreate, HttpProtocol } from '$lib/types/scan-context';

type CtxLike = ScanContextRead | ScanContextCreate;

export type FacetKey = 'auth' | 'headers' | 'rate' | 'scope' | 'runtime' | 'proxy';

export interface ContextFacet {
	key: FacetKey;
	label: string;
	set: boolean;
	value: string;
}

export const FACET_LABELS: Record<FacetKey, string> = {
	auth: 'Auth',
	headers: 'Headers',
	rate: 'Rate',
	scope: 'Scope',
	runtime: 'Runtime',
	proxy: 'Proxy'
};

const HTTP_PROTOCOL_LABELS: Record<HttpProtocol, string> = {
	both: '',
	http_only: 'HTTP only',
	https_only: 'HTTPS only'
};

export const PASS_THROUGH = 'No overrides: engine settings apply unchanged';

export function authBadgeLabel(ctx: CtxLike): string {
	switch (ctx.auth_type) {
		case 'bearer':
			return 'Bearer';
		case 'basic': {
			const user = ctx.auth?.basic_username;
			return user ? `Basic (${user})` : 'Basic';
		}
		case 'header':
			return ctx.auth?.header_name || 'Header';
		case 'cookie':
			return 'Cookie';
		case 'api_key':
			return ctx.auth?.api_key_name || 'API Key';
		case 'none':
		default:
			return 'No auth';
	}
}

export function authLabel(ctx: CtxLike): string {
	switch (ctx.auth_type) {
		case 'bearer':
			return 'Bearer token';
		case 'basic': {
			const user = ctx.auth?.basic_username;
			return user ? `Basic auth as ${user}` : 'Basic auth';
		}
		case 'header':
			return `${ctx.auth?.header_name || 'Custom'} header`;
		case 'cookie':
			return 'Session cookie';
		case 'api_key':
			return `${ctx.auth?.api_key_name || 'API'} key`;
		case 'none':
		default:
			return 'None';
	}
}

function plural(n: number, word: string, pluralWord = `${word}s`): string {
	return `${n} ${n === 1 ? word : pluralWord}`;
}

function listOf(items: string[], max: number): string {
	const shown = items.slice(0, max).join(', ');
	const rest = items.length - max;
	return rest > 0 ? `${shown} +${rest}` : shown;
}

export function countExclusions(ctx: CtxLike): number {
	return (
		ctx.excluded_subdomains.length +
		ctx.excluded_paths.length +
		ctx.excluded_ips.length +
		ctx.included_subdomains.length
	);
}

export function countOverrides(ctx: CtxLike): number {
	let n = 0;
	if (ctx.global_rate_limit_override != null) n++;
	n += Object.keys(ctx.per_tool_rate_overrides).length;
	if (ctx.thread_multiplier !== 1.0) n++;
	if (ctx.timeout_multiplier !== 1.0) n++;
	if (ctx.follow_redirects_override != null) n++;
	if (ctx.http_protocol !== 'both') n++;
	return n;
}

export function contextFacets(ctx: CtxLike, proxyName?: string | null): ContextFacet[] {
	const headerNames = ctx.extra_headers.map((h) => h.name).filter(Boolean);

	const rate: string[] = [];
	if (ctx.global_rate_limit_override != null) rate.push(`${ctx.global_rate_limit_override}/s cap`);
	for (const [tool, value] of Object.entries(ctx.per_tool_rate_overrides)) {
		rate.push(`${tool} ${value}/s`);
	}
	if (ctx.thread_multiplier !== 1.0) rate.push(`threads ×${ctx.thread_multiplier}`);
	if (ctx.timeout_multiplier !== 1.0) rate.push(`timeouts ×${ctx.timeout_multiplier}`);

	const scope: string[] = [];
	if (ctx.included_subdomains.length) {
		scope.push(`only ${plural(ctx.included_subdomains.length, 'included host')}`);
	}
	if (ctx.excluded_subdomains.length) {
		scope.push(plural(ctx.excluded_subdomains.length, 'excluded pattern'));
	}
	if (ctx.excluded_paths.length) scope.push(plural(ctx.excluded_paths.length, 'excluded path'));
	if (ctx.excluded_ips.length) {
		scope.push(plural(ctx.excluded_ips.length, 'excluded IP', 'excluded IPs'));
	}

	const runtime: string[] = [];
	const proto = HTTP_PROTOCOL_LABELS[ctx.http_protocol];
	if (proto) runtime.push(proto);
	if (ctx.follow_redirects_override != null) {
		runtime.push(
			ctx.follow_redirects_override ? 'always follow redirects' : 'never follow redirects'
		);
	}

	const auth = ctx.auth_type !== 'none';
	return [
		{ key: 'auth', label: FACET_LABELS.auth, set: auth, value: auth ? authLabel(ctx) : 'None' },
		{
			key: 'headers',
			label: FACET_LABELS.headers,
			set: headerNames.length > 0,
			value: headerNames.length ? listOf(headerNames, 3) : 'None'
		},
		{
			key: 'rate',
			label: FACET_LABELS.rate,
			set: rate.length > 0,
			value: rate.length ? rate.join(' · ') : 'Engine defaults'
		},
		{
			key: 'scope',
			label: FACET_LABELS.scope,
			set: scope.length > 0,
			value: scope.length ? scope.join(' · ') : 'Everything discovered'
		},
		{
			key: 'runtime',
			label: FACET_LABELS.runtime,
			set: runtime.length > 0,
			value: runtime.length ? runtime.join(' · ') : 'Engine defaults'
		},
		{
			key: 'proxy',
			label: FACET_LABELS.proxy,
			set: Boolean(ctx.proxy_id),
			value: ctx.proxy_id ? (proxyName ?? 'Proxy set') : 'Direct'
		}
	];
}

export function facetLine(ctx: CtxLike, proxyName?: string | null): string {
	const set = contextFacets(ctx, proxyName).filter((f) => f.set);
	return set.length ? set.map((f) => f.value).join(' · ') : PASS_THROUGH;
}

export const buildContextSummary = facetLine;
