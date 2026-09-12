import { REFUSAL } from '$lib/config/compare';
import { isLiveStatus } from '$lib/utilities/scan-status';
import type { ScanRead } from '$lib/types/scan';

export interface Eligibility {
	ok: boolean;
	reason: string;
	baseline?: ScanRead;
	current?: ScanRead;
}

const started = (s: ScanRead) => new Date(s.started_at ?? s.created_at).getTime();

/** Why this pair can or cannot be compared. */
export function eligibility(scans: ScanRead[]): Eligibility {
	if (scans.length < 2) return { ok: false, reason: REFUSAL.NEED_ONE_MORE };
	if (scans.length > 2) return { ok: false, reason: REFUSAL.TOO_MANY };

	const [baseline, current] = [...scans].sort((a, b) => started(a) - started(b));
	if (baseline.id === current.id) return { ok: false, reason: REFUSAL.SAME_RUN };
	if (baseline.target_id !== current.target_id) {
		return { ok: false, reason: REFUSAL.DIFFERENT_TARGET };
	}
	if (isLiveStatus(baseline.status) || isLiveStatus(current.status)) {
		return { ok: false, reason: REFUSAL.UNFINISHED };
	}
	if (baseline.scope !== current.scope) {
		return {
			ok: false,
			reason: current.scope === 'full' ? REFUSAL.FOCUSED_AGAINST_FULL : REFUSAL.FULL_AGAINST_FOCUSED
		};
	}
	return { ok: true, reason: '', baseline, current };
}
