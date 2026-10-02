import type { AiCall, AiProvider } from '$lib/types/ai';

export const AIProvider = {
	OPENAI: 'openai',
	ANTHROPIC: 'anthropic',
	GOOGLE: 'google',
	OPENAI_COMPATIBLE: 'openai_compatible'
} as const;

export const DEFAULT_AI_PROVIDER = AIProvider.ANTHROPIC;

export const MAX_CONNECTION_NAME = 60;

/** Mirror of shared/definitions/ai.py:MAX_CALLS_PAGE. */
export const CALLS_PAGE = 50;
export const RECENT_CALLS = 5;

const RATE = new Intl.NumberFormat('en-US', {
	style: 'currency',
	currency: 'USD',
	minimumFractionDigits: 2,
	maximumFractionDigits: 4
});
const COST = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const SMALLEST_COST = 0.005;

export function formatRate(perMtok: number | null): string {
	return perMtok === null ? '' : RATE.format(perMtok);
}

export function formatCost(usd: number | null): string {
	if (usd === null) return '—';
	if (usd > 0 && usd < SMALLEST_COST) return '<$0.01';
	return COST.format(usd);
}

export function callCursor(call: Pick<AiCall, 'at' | 'id'>): string {
	return `${call.at},${call.id}`;
}

function serverHost(baseUrl: string): string {
	try {
		return new URL(baseUrl.trim()).hostname;
	} catch {
		return '';
	}
}

/** Mirror of shared/definitions/ai.py:connection_name plus the service's suffix. */
export function connectionName(
	spec: Pick<AiProvider, 'label' | 'needs_base_url'> | undefined,
	baseUrl: string,
	taken: readonly string[] = []
): string {
	if (!spec) return '';
	const host = spec.needs_base_url ? serverHost(baseUrl) : '';
	const base = (host || spec.label).slice(0, MAX_CONNECTION_NAME);
	const used = new Set(taken.map((name) => name.toLowerCase()));
	let candidate = base;
	for (let n = 2; used.has(candidate.toLowerCase()); n++) {
		const suffix = ` ${n}`;
		candidate = `${base.slice(0, MAX_CONNECTION_NAME - suffix.length)}${suffix}`;
	}
	return candidate;
}
