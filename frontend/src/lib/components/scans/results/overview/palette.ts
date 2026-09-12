import type { StatusClass } from '$lib/utilities/scan-correlation';

export const CHART_FILL: Record<StatusClass, string> = {
	success: 'var(--success)',
	info: 'var(--info)',
	warning: 'var(--warning)',
	destructive: 'var(--destructive)',
	muted: 'color-mix(in oklch, var(--muted-foreground) 35%, transparent)'
};
