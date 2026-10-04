export enum Evidence {
	INFERRED = 'inferred',
	OBSERVED = 'observed',
	CROSS_CHECKED = 'cross-checked',
	PROVEN = 'proven'
}

export const EVIDENCE_ORDER: string[] = [
	Evidence.INFERRED,
	Evidence.OBSERVED,
	Evidence.CROSS_CHECKED,
	Evidence.PROVEN
];

export const EVIDENCE_LABELS: Record<string, string> = {
	[Evidence.INFERRED]: 'Inferred',
	[Evidence.OBSERVED]: 'Observed',
	[Evidence.CROSS_CHECKED]: 'Cross-checked',
	[Evidence.PROVEN]: 'Proven'
};

export const EVIDENCE_HELP: Record<string, string> = {
	[Evidence.INFERRED]: 'The reported version falls inside the affected range.',
	[Evidence.OBSERVED]: 'A check matched the response it received.',
	[Evidence.CROSS_CHECKED]: 'Two independent signals agree at the same location.',
	[Evidence.PROVEN]: 'The asset produced an out-of-band interaction.'
};

export const CROSS_CHECKED_TOKEN = `is:${Evidence.CROSS_CHECKED}`;

export function evidenceRank(value: string | null | undefined): number {
	return EVIDENCE_ORDER.indexOf(value ?? '');
}

export function evidenceLabel(value: string | null | undefined): string {
	return EVIDENCE_LABELS[value ?? ''] ?? '';
}

export function evidenceToken(value: string): string {
	return `evidence:${value}`;
}
