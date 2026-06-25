export type Severity = 'critical' | 'high' | 'medium' | 'low';

export const SEVERITIES: readonly Severity[] = ['critical', 'high', 'medium', 'low'] as const;

export const SEVERITY_DOT: Record<Severity, string> = {
	critical: 'var(--destructive)',
	high: 'var(--warning)',
	medium: 'var(--muted-foreground)',
	low: 'var(--muted-foreground)'
};
