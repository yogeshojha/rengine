import type { StatusClass } from '$lib/utilities/scan-correlation';

export const CHART_FILL: Record<StatusClass, string> = {
	success: 'var(--chart-2)',
	info: 'var(--chart-1)',
	warning: 'var(--chart-4)',
	destructive: 'var(--destructive)',
	muted: 'color-mix(in oklch, var(--muted-foreground) 35%, transparent)'
};
