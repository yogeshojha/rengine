export enum Evidence {
	INFERRED = 'inferred',
	OBSERVED = 'observed',
	CORROBORATED = 'corroborated',
	PROVEN = 'proven'
}

export const EVIDENCE_ORDER: string[] = [
	Evidence.INFERRED,
	Evidence.OBSERVED,
	Evidence.CORROBORATED,
	Evidence.PROVEN
];

export const EVIDENCE_LABELS: Record<string, string> = {
	[Evidence.INFERRED]: 'Inferred',
	[Evidence.OBSERVED]: 'Observed',
	[Evidence.CORROBORATED]: 'Corroborated',
	[Evidence.PROVEN]: 'Proven'
};

export const EVIDENCE_HELP: Record<string, string> = {
	[Evidence.INFERRED]:
		'A reported version falls inside the affected range. Nothing was sent to the asset.',
	[Evidence.OBSERVED]: 'A check sent a request and its matcher fired.',
	[Evidence.CORROBORATED]: 'Two independent signals agree at the same location.',
	[Evidence.PROVEN]:
		'The asset returned an artifact only a vulnerable one returns, such as an out-of-band callback.'
};

export function evidenceRank(value: string | null | undefined): number {
	return EVIDENCE_ORDER.indexOf(value ?? '');
}

export function evidenceLabel(value: string | null | undefined): string {
	return EVIDENCE_LABELS[value ?? ''] ?? '';
}

export function evidenceToken(value: string): string {
	return `evidence:${value}`;
}
