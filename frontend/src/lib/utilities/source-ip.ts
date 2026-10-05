import {
	FAMILY_ORDER,
	SOURCE_IP_FAILURE_LABELS,
	SOURCE_IP_OFF_REASON,
	SourceIpPhase,
	SourceIpState,
	type AddressFamily
} from '$lib/config/source-ip';
import { isOpenStatus } from '$lib/utilities/scan-status';
import type { ScanRead, SourceIpCheck } from '$lib/types/scan';

export interface SourceIpRow {
	family: AddressFamily;
	address: string;
	changedTo: string | null;
}

export type SourceIpView =
	| { kind: 'hidden' }
	| { kind: 'checking' }
	| { kind: 'not_measured'; reason: string | null }
	| { kind: 'measured'; rows: SourceIpRow[]; proxied: boolean; endFailure: string | null };

function failureLabel(check: SourceIpCheck | undefined): string | null {
	return check?.failure ? (SOURCE_IP_FAILURE_LABELS[check.failure] ?? null) : null;
}

export function sourceIpView(scan: Pick<ScanRead, 'status' | 'source_ip'>): SourceIpView {
	if (scan.status === 'pending') return { kind: 'hidden' };
	const record = scan.source_ip;
	if (!record) return { kind: 'not_measured', reason: null };
	if (record.state === SourceIpState.OFF)
		return { kind: 'not_measured', reason: SOURCE_IP_OFF_REASON };

	const start = record.checks.find((c) => c.phase === SourceIpPhase.START);
	const end = record.checks.find((c) => c.phase === SourceIpPhase.END);
	if (!start && !end) {
		return isOpenStatus(scan.status)
			? { kind: 'checking' }
			: { kind: 'not_measured', reason: null };
	}

	const rows: SourceIpRow[] = [];
	for (const family of FAMILY_ORDER) {
		const first = start?.[family] ?? null;
		const last = end?.[family] ?? null;
		const address = first ?? last;
		if (!address) continue;
		rows.push({ family, address, changedTo: first && last && first !== last ? last : null });
	}
	if (!rows.length)
		return { kind: 'not_measured', reason: failureLabel(start) ?? failureLabel(end) };

	const startAnswered = !!start && FAMILY_ORDER.some((f) => start[f]);
	return {
		kind: 'measured',
		rows,
		proxied: (start ?? end)?.proxied ?? false,
		endFailure: startAnswered ? failureLabel(end) : null
	};
}
