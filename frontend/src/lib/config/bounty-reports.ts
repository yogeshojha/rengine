import { Severity } from './vulnerabilities';
import { ReportStage } from '$lib/types/bounty-report';

export const REPORT_PAGE_SIZE = 25;
export const REPORT_PAGE_SIZES = [10, 25, 50, 100];

export const REPORT_STAGE_FILL: Record<string, string> = {
	[ReportStage.Open]: 'var(--info)',
	[ReportStage.Resolved]: 'var(--success)',
	[ReportStage.Closed]: 'var(--muted-foreground)'
};

export const REPORT_STAGE_ORDER: ReportStage[] = [
	ReportStage.Open,
	ReportStage.Resolved,
	ReportStage.Closed
];

// platform severity "none" draws as info
export const REPORT_SEVERITY_KEY: Record<string, string> = {
	critical: Severity.CRITICAL,
	high: Severity.HIGH,
	medium: Severity.MEDIUM,
	low: Severity.LOW,
	none: Severity.INFO
};

export const REPORT_SAVED_VIEWS: { label: string; states?: string[]; severities?: string[] }[] = [
	{ label: 'Critical and high', severities: ['critical', 'high'] },
	{ label: 'Needs more info', states: ['needs-more-info'] },
	{ label: 'Duplicates', states: ['duplicate'] },
	{ label: 'Informative', states: ['informative'] }
];

const MONEY = new Map<string, Intl.NumberFormat>();

export function formatMoney(amount: number, currency: string): string {
	let fmt = MONEY.get(currency);
	if (!fmt) {
		try {
			fmt = new Intl.NumberFormat('en', {
				style: 'currency',
				currency,
				maximumFractionDigits: 0
			});
		} catch {
			fmt = new Intl.NumberFormat('en', { maximumFractionDigits: 0 });
		}
		MONEY.set(currency, fmt);
	}
	return fmt.format(amount);
}

export function formatMonies(list: { amount: number; currency: string }[]): string {
	return list.map((m) => formatMoney(m.amount, m.currency)).join(' · ');
}
