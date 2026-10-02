import { describe, expect, it } from 'vitest';
import { briefTabs } from './brief-tabs.svelte';

type Tab = 'asset' | 'evidence' | 'intel';

describe('briefTabs', () => {
	it('opens a row on the first tab', () => {
		expect(briefTabs<Tab>('asset').of('a')).toBe('asset');
	});

	it('keeps each row on its own tab', () => {
		const tabs = briefTabs<Tab>('asset');
		tabs.set('a', 'intel');
		tabs.set('b', 'evidence');
		expect([tabs.of('a'), tabs.of('b'), tabs.of('c')]).toEqual(['intel', 'evidence', 'asset']);
	});

	it('reopens a closed row on the first tab', () => {
		const tabs = briefTabs<Tab>('asset');
		tabs.set('a', 'intel');
		tabs.close('a');
		expect(tabs.of('a')).toBe('asset');
	});
});
