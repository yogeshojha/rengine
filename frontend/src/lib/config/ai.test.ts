import { describe, expect, it } from 'vitest';
import { MAX_CONNECTION_NAME, callCursor, connectionName, formatCost, formatRate } from './ai';

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
