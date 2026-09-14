import { describe, expect, it } from 'vitest';
import { summarize } from './engine-summary';
import type { StageCatalogEntry } from '$lib/types/scan-engine';

function stage(
	name: string,
	over: Partial<StageCatalogEntry> & { rates?: Record<string, number | null> }
): StageCatalogEntry {
	const { rates, ...rest } = over;
	return {
		name,
		title: name,
		description: '',
		phase: 'expansion',
		level: 0,
		applies_to: ['domain'],
		tools: [],
		api_keys: [],
		requires_api_keys: false,
		touches_target: true,
		launch_fields: [],
		group: 'web',
		role: 'capability',
		consumes: [],
		produces: [],
		transport: rates
			? { tool: 'httpx', rates, threads: { normal: 1, aggressive: 2 }, timeout: 10 }
			: null,
		defaults: { enabled: true },
		fields: [],
		...rest
	};
}

const catalog = [
	stage('http_probe', { rates: { passive: 150, normal: 150, aggressive: 400 } }),
	stage('port_scan', { rates: { passive: 1000, normal: 1000, aggressive: 3000 } }),
	stage('reverse_dns', {
		touches_target: false,
		rates: { passive: null, normal: null, aggressive: null }
	})
];

describe('summarize', () => {
	it('reads the rate off the served transport for the run intensity', () => {
		expect(summarize({}, catalog, 'normal').requestsPerSecond).toBe(1150);
		expect(summarize({}, catalog, 'aggressive').requestsPerSecond).toBe(3400);
	});

	it('counts nothing at passive and reports the blocked stages', () => {
		const passive = summarize({}, catalog, 'passive');
		expect(passive.requestsPerSecond).toBe(0);
		expect(passive.footprint).toBe('none');
		expect(passive.headline).toContain('2 blocked by passive');
	});

	it('drops a stage the engine switched off', () => {
		const quiet = summarize({ port_scan: { enabled: false } }, catalog, 'normal');
		expect(quiet.requestsPerSecond).toBe(150);
		expect(quiet.footprint).toBe('quiet');
	});
});
