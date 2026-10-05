import { describe, expect, it } from 'vitest';
import {
	SOURCE_IP_FAILURE_LABELS,
	SOURCE_IP_OFF_REASON,
	SourceIpFailure,
	SourceIpPhase,
	SourceIpState
} from '$lib/config/source-ip';
import type { ScanStatus, SourceIpCheck, SourceIpRecord } from '$lib/types/scan';
import { sourceIpView } from './source-ip';

const AT = '2026-10-05T03:00:00Z';

function check(phase: SourceIpPhase, fields: Partial<SourceIpCheck> = {}): SourceIpCheck {
	return {
		phase,
		checked_at: AT,
		proxied: false,
		ipv4: null,
		ipv6: null,
		failure: null,
		...fields
	};
}

function measured(...checks: SourceIpCheck[]): SourceIpRecord {
	return { state: SourceIpState.MEASURED, checks };
}

function view(status: ScanStatus, source_ip: SourceIpRecord | null) {
	return sourceIpView({ status, source_ip });
}

describe('sourceIpView', () => {
	it('hides a run that has not started', () => {
		expect(view('pending', null)).toEqual({ kind: 'hidden' });
	});

	it('reports a run with no record as not measured, with no reason', () => {
		expect(view('completed', null)).toEqual({ kind: 'not_measured', reason: null });
	});

	it('names the setting when lookups were off', () => {
		expect(view('completed', { state: SourceIpState.OFF, checks: [] })).toEqual({
			kind: 'not_measured',
			reason: SOURCE_IP_OFF_REASON
		});
	});

	it('is checking while a live run waits for its first answer', () => {
		expect(view('running', measured())).toEqual({ kind: 'checking' });
		expect(view('paused', measured())).toEqual({ kind: 'checking' });
		expect(view('failed', measured())).toEqual({ kind: 'not_measured', reason: null });
	});

	it('shows the start address while the run is open', () => {
		const record = measured(check(SourceIpPhase.START, { ipv4: '203.0.113.7' }));
		expect(view('running', record)).toEqual({
			kind: 'measured',
			rows: [{ family: 'ipv4', address: '203.0.113.7', changedTo: null }],
			proxied: false,
			endFailure: null
		});
	});

	it('shows one address when start and end agree, and both when they differ', () => {
		const record = measured(
			check(SourceIpPhase.START, { ipv4: '203.0.113.7', ipv6: '2001:db8::7', proxied: true }),
			check(SourceIpPhase.END, { ipv4: '198.51.100.4', ipv6: '2001:db8::7', proxied: true })
		);
		expect(view('completed', record)).toEqual({
			kind: 'measured',
			rows: [
				{ family: 'ipv4', address: '203.0.113.7', changedTo: '198.51.100.4' },
				{ family: 'ipv6', address: '2001:db8::7', changedTo: null }
			],
			proxied: true,
			endFailure: null
		});
	});

	it('keeps the start address and names a failed end check', () => {
		const record = measured(
			check(SourceIpPhase.START, { ipv4: '203.0.113.7' }),
			check(SourceIpPhase.END, { failure: SourceIpFailure.TIMEOUT })
		);
		const result = view('cancelled', record);
		expect(result.kind).toBe('measured');
		expect(result.kind === 'measured' && result.endFailure).toBe(
			SOURCE_IP_FAILURE_LABELS[SourceIpFailure.TIMEOUT]
		);
	});

	it('gives the failure as the reason when no check answered', () => {
		const record = measured(
			check(SourceIpPhase.START, { failure: SourceIpFailure.PROXY, proxied: true }),
			check(SourceIpPhase.END, { failure: SourceIpFailure.UNREACHABLE, proxied: true })
		);
		expect(view('completed', record)).toEqual({
			kind: 'not_measured',
			reason: SOURCE_IP_FAILURE_LABELS[SourceIpFailure.PROXY]
		});
	});

	it('labels every failure', () => {
		for (const failure of Object.values(SourceIpFailure)) {
			expect(SOURCE_IP_FAILURE_LABELS[failure]).toBeTruthy();
		}
	});
});
