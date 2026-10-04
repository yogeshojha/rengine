import { describe, expect, it } from 'vitest';
import {
	CostSource,
	MAX_CONNECTION_NAME,
	cacheHint,
	callCursor,
	connectionName,
	costHint,
	formatCost,
	formatRate,
	ratePair,
	unpricedLabel
} from './ai';

const ANTHROPIC = { label: 'Anthropic', needs_base_url: false };
const COMPATIBLE = { label: 'OpenAI-compatible', needs_base_url: true };

describe('connectionName', () => {
	it('takes the provider label, or the server host for a server provider', () => {
		expect(connectionName(ANTHROPIC, 'https://ignored.example/v1')).toBe('Anthropic');
		expect(connectionName(COMPATIBLE, 'https://openrouter.ai/api/v1')).toBe('openrouter.ai');
		expect(connectionName(COMPATIBLE, 'http://ollama:11434/v1')).toBe('ollama');
		expect(connectionName(COMPATIBLE, 'not a url')).toBe('OpenAI-compatible');
	});

	it('numbers a name that is taken, ignoring case', () => {
		expect(connectionName(ANTHROPIC, '', ['anthropic'])).toBe('Anthropic 2');
		expect(connectionName(ANTHROPIC, '', ['Anthropic', 'Anthropic 2'])).toBe('Anthropic 3');
	});

	it('stays within the stored width', () => {
		const host = `${'a'.repeat(70)}.example`;
		const name = connectionName(COMPATIBLE, `https://${host}/v1`, [
			host.slice(0, MAX_CONNECTION_NAME)
		]);
		expect(name.length).toBeLessThanOrEqual(MAX_CONNECTION_NAME);
		expect(name.endsWith(' 2')).toBe(true);
	});
});

describe('prices', () => {
	it('reads a price per million tokens to the cent, or finer below a cent', () => {
		expect(formatRate(2)).toBe('$2.00');
		expect(formatRate(1.26)).toBe('$1.26');
		expect(formatRate(0.075)).toBe('$0.075');
		expect(formatRate(0)).toBe('$0.00');
		expect(formatRate(null)).toBe('');
	});

	it('reads a cost to the cent and marks a cost under a cent', () => {
		expect(formatCost(1.2096)).toBe('$1.21');
		expect(formatCost(0.000225)).toBe('<$0.01');
		expect(formatCost(0)).toBe('$0.00');
		expect(formatCost(null)).toBe('—');
	});
});

describe('callCursor', () => {
	it('joins the last row of a page into the next cursor', () => {
		expect(callCursor({ at: '2026-10-02T06:23:09.313941Z', id: 'a1' })).toBe(
			'2026-10-02T06:23:09.313941Z,a1'
		);
	});
});

describe('cost hints', () => {
	const listed = { cost_source: CostSource.LIST, input_per_mtok: 4, output_per_mtok: 20 };

	it('names the provider that reported a cost', () => {
		expect(
			costHint(
				{ cost_source: CostSource.PROVIDER, input_per_mtok: null, output_per_mtok: null },
				'OpenAI-compatible'
			)
		).toBe('Reported by OpenAI-compatible');
	});

	it('states the list rates a cost was priced at', () => {
		expect(costHint(listed, 'Anthropic')).toBe('List price, $4.00 and $20.00 per 1M tokens');
		expect(costHint({ ...listed, input_per_mtok: null }, 'Anthropic')).toBe('List price');
		expect(costHint({ ...listed, cost_source: null }, 'Anthropic')).toBeNull();
	});

	it('names no source it does not know', () => {
		expect(costHint({ ...listed, cost_source: 'other' }, 'Anthropic')).toBeNull();
	});

	it('writes a rate pair per million tokens', () => {
		expect(ratePair(0.3, 1.2)).toBe('$0.30 and $1.20 per 1M tokens');
		expect(ratePair(0.075, 3.75)).toBe('$0.075 and $3.75 per 1M tokens');
	});

	it('counts cached input, and nothing when none was cached', () => {
		expect(cacheHint(1536, 0)).toBe('1,536 read from cache');
		expect(cacheHint(1536, 200)).toBe('1,536 read from cache · 200 written to cache');
		expect(cacheHint(0, 0)).toBeNull();
	});

	it('names unpriced calls only when some exist', () => {
		expect(unpricedLabel(3)).toBe('3 unpriced');
		expect(unpricedLabel(0)).toBeNull();
	});
});
