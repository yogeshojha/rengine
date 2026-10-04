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

/** Mirror of shared/definitions/ai.py:CostSource. */
export const CostSource = {
	PROVIDER: 'provider',
	LIST: 'list'
} as const;

const PRICE_LABELS: Record<string, string> = {
	[CostSource.LIST]: 'List price'
};

const RATE = new Intl.NumberFormat('en-US', {
	style: 'currency',
	currency: 'USD',
	minimumFractionDigits: 2,
	maximumFractionDigits: 4
});
const COST = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
const COUNT = new Intl.NumberFormat('en-US');
const SMALLEST_COST = 0.005;

export function formatRate(perMtok: number | null): string {
	return perMtok === null ? '' : RATE.format(perMtok);
}

export function formatCost(usd: number | null): string {
	if (usd === null) return '—';
	if (usd > 0 && usd < SMALLEST_COST) return '<$0.01';
	return COST.format(usd);
}

/** Where a call's cost came from. */
export function costHint(
	call: Pick<AiCall, 'cost_source' | 'input_per_mtok' | 'output_per_mtok'>,
	providerLabel: string
): string | null {
	if (call.cost_source === CostSource.PROVIDER) return `Reported by ${providerLabel}`;
	const label = call.cost_source ? PRICE_LABELS[call.cost_source] : undefined;
	if (!label) return null;
	if (call.input_per_mtok === null || call.output_per_mtok === null) return label;
	return `${label}, ${ratePair(call.input_per_mtok, call.output_per_mtok)}`;
}

export function ratePair(input: number, output: number): string {
	return `${formatRate(input)} and ${formatRate(output)} per 1M tokens`;
}

export function cacheHint(reads: number, writes: number): string | null {
	const parts: string[] = [];
	if (reads) parts.push(`${COUNT.format(reads)} read from cache`);
	if (writes) parts.push(`${COUNT.format(writes)} written to cache`);
	return parts.length ? parts.join(' · ') : null;
}

export function unpricedLabel(count: number): string | null {
	return count ? `${COUNT.format(count)} unpriced` : null;
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
