import { describe, expect, it } from 'vitest';
import { baselineStages, resolvePlan } from './launch-plan';
import type { EngineCatalog, StageCatalogEntry } from '$lib/types/scan-engine';

function stage(name: string, over: Partial<StageCatalogEntry>): StageCatalogEntry {
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
		defaults: { enabled: true },
		fields: [],
		...over
	};
}

const stages = [
	stage('subdomain_discovery', { passive_capable: true, produces: ['hosts'] }),
	stage('http_probe', {
		level: 1,
		role: 'support',
		always_on: true,
		consumes: ['hosts'],
		produces: ['http_assets']
	}),
	stage('waf_detect', { level: 2, role: 'support', consumes: ['http_assets'] }),
	stage('vulnerability_scan', { level: 2, consumes: ['http_assets'] })
];

const catalog = {
	stages,
	seed_produces: { domain: ['hosts'] }
} as unknown as EngineCatalog;

function plan(on: string[], intensity: 'passive' | 'normal' = 'normal') {
	const effective = baselineStages(stages, null);
	for (const s of stages) {
		if (!s.always_on) effective[s.name] = { ...effective[s.name], enabled: on.includes(s.name) };
	}
	return resolvePlan(catalog, effective, 'domain', intensity);
}

describe('resolvePlan', () => {
	it('includes the probe automatically and feeds the scanner from it', () => {
		const result = plan(['vulnerability_scan']);
		expect(result.states.get('http_probe')).toBe('implied');
		expect(result.states.get('vulnerability_scan')).toBe('on');
		expect(result.states.get('subdomain_discovery')).toBe('off');
		expect(result.unsatisfied.size).toBe(0);
	});

	it('never writes a switch for the probe into the run', () => {
		expect(plan(['vulnerability_scan']).effective.http_probe.enabled).toBe(true);
		expect(plan([]).effective.http_probe.enabled).toBe(true);
	});

	it('does not count the probe as a reason to add active support', () => {
		const result = plan(['subdomain_discovery'], 'passive');
		expect(result.states.get('http_probe')).toBe('off');
		expect(result.states.get('waf_detect')).toBe('off');
	});

	it('runs nothing when nothing is selected', () => {
		expect(plan([]).states.get('http_probe')).toBe('off');
	});
});
