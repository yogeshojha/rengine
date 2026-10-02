import { describe, expect, it } from 'vitest';
import {
	activitySummary,
	scanCountPills,
	formatSeconds,
	elapsedSeconds,
	elapsedText,
	scanStatusTabCount
} from './scan-status';
import { SURFACE_ORDER } from '$lib/config/surface';
import type { ScanRead, ScanStatusCounts } from '$lib/types/scan';

function scan(over: Partial<ScanRead> = {}): ScanRead {
	return {
		id: 'scan-a',
		target_id: 'target-a',
		scope: 'full',
		status: 'completed',
		subdomains_found: 0,
		http_assets_found: 0,
		ips_found: 0,
		open_ports_found: 0,
		endpoints_found: 0,
		vulnerabilities_found: 0,
		secrets_found: 0,
		...over
	} as ScanRead;
}

describe('scanCountPills', () => {
	it('carries every dimension that has a count column', () => {
		const keys = scanCountPills(scan()).map((p) => p.key);
		for (const spec of SURFACE_ORDER) {
			if (spec.countColumns.length) expect(keys).toContain(spec.key);
		}
	});

	it('reports a run that found only secrets', () => {
		const pills = scanCountPills(scan({ secrets_found: 12 })).filter((p) => p.value > 0);
		expect(pills.map((p) => p.key)).toEqual(['secrets']);
	});

	it('emphasises findings only when there are some', () => {
		expect(scanCountPills(scan()).find((p) => p.key === 'vulnerabilities')?.emphasis).toBe(false);
		expect(
			scanCountPills(scan({ vulnerabilities_found: 3 })).find((p) => p.key === 'vulnerabilities')
				?.emphasis
		).toBe(true);
	});
});

describe('elapsedText', () => {
	it('drops seconds', () => {
		expect(elapsedText(45)).toBe('<1m');
		expect(elapsedText(931)).toBe('15m');
		expect(elapsedText(3660)).toBe('1h 1m');
		expect(elapsedText(7200)).toBe('2h');
	});
});

describe('formatSeconds', () => {
	it('drops the empty part', () => {
		expect(formatSeconds(45)).toBe('45s');
		expect(formatSeconds(120)).toBe('2m');
		expect(formatSeconds(125)).toBe('2m 5s');
		expect(formatSeconds(7200)).toBe('2h');
		expect(formatSeconds(7260)).toBe('2h 1m');
	});
});

describe('elapsedSeconds', () => {
	const started = '2026-09-16T10:00:00Z';
	const now = Date.parse('2026-09-16T10:10:00Z');

	it('counts only a run that is still moving', () => {
		expect(elapsedSeconds(scan({ status: 'running', started_at: started }), now)).toBe(600);
		expect(elapsedSeconds(scan({ status: 'completed', started_at: started }), now)).toBeNull();
		expect(elapsedSeconds(scan({ status: 'paused', started_at: started }), now)).toBeNull();
	});

	it('takes paused time out of the clock and never goes below zero', () => {
		expect(
			elapsedSeconds(scan({ status: 'running', started_at: started, paused_seconds: 60 }), now)
		).toBe(540);
		expect(
			elapsedSeconds(scan({ status: 'running', started_at: started, paused_seconds: 9999 }), now)
		).toBe(0);
	});
});

describe('scanStatusTabCount', () => {
	const counts = {
		pending: 1,
		running: 2,
		paused: 3,
		completed: 4,
		failed: 5,
		cancelled: 6
	} as ScanStatusCounts;

	it('sums the statuses a tab stands for', () => {
		expect(scanStatusTabCount('all', counts, 99)).toBe(99);
		expect(scanStatusTabCount('active', counts, 99)).toBe(3);
		expect(scanStatusTabCount('paused', counts, 99)).toBe(3);
	});
});

describe('activitySummary', () => {
	it('prints the labels the server sent, never the raw keys', () => {
		expect(
			activitySummary([
				{ key: 'endpoints', value: 1200, label: 'endpoints' },
				{ key: 'endpoints_new', value: 0, label: 'new endpoints' }
			])
		).toBe('1,200 endpoints · 0 new endpoints');
		expect(activitySummary(undefined)).toBe('');
	});
});
