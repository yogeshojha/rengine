import type { ScanContextRead, ScanContextCreate, HttpProtocol } from '$lib/types/scan-context';

type CtxLike = ScanContextRead | ScanContextCreate;

const HTTP_PROTOCOL_LABELS: Record<HttpProtocol, string> = {
	both: '',
	http_only: 'http-only',
	https_only: 'https-only'
};

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

function plural(n: number, word: string): string {
	return `${n} ${word}${n === 1 ? '' : 's'}`;
}

export function buildContextSummary(ctx: CtxLike): string {
	const parts: string[] = [];

	if (ctx.auth_type !== 'none') {
		parts.push(`${authBadgeLabel(ctx)} auth`);
	}

	if (ctx.extra_headers.length > 0) {
		parts.push(plural(ctx.extra_headers.length, 'header'));
	}

	if (ctx.global_rate_limit_override != null) {
		parts.push(`global rate ${ctx.global_rate_limit_override}`);
	}

	const toolOverrides = Object.keys(ctx.per_tool_rate_overrides).length;
	if (toolOverrides > 0) {
		parts.push(plural(toolOverrides, 'tool rate'));
	}

	if (ctx.thread_multiplier !== 1.0) {
		parts.push(`threads ×${ctx.thread_multiplier}`);
	}

	if (ctx.timeout_multiplier !== 1.0) {
		parts.push(`timeout ×${ctx.timeout_multiplier}`);
	}

	const exclusions = countExclusions(ctx);
	if (exclusions > 0) {
		parts.push(plural(exclusions, 'exclusion'));
	}

	if (ctx.follow_redirects_override != null) {
		parts.push(ctx.follow_redirects_override ? 'follow redirects' : 'no redirects');
	}

	const proto = HTTP_PROTOCOL_LABELS[ctx.http_protocol];
	if (proto) {
		parts.push(proto);
	}

	if (parts.length === 0) {
		return 'Pass-through (no auth, no overrides)';
	}

	return parts.join(' · ');
}
