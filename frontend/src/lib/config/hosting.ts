export type Fronting = 'edge' | 'cloud' | 'direct';

export const FRONTING_FILL: Record<Fronting, string> = {
	edge: 'var(--chart-1)',
	cloud: 'var(--chart-3)',
	direct: 'var(--chart-4)'
};

export const frontingFill = (kind: string) => FRONTING_FILL[kind as Fronting] ?? 'var(--series)';
