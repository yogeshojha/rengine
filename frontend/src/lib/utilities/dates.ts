export const MS_PER_DAY = 1000 * 60 * 60 * 24;

export const formatDate = (dateString: string) => {
	const date = new Date(dateString);
	return date.toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
};

const UNITS: [minutes: number, short: string, long: string][] = [
	[60 * 24 * 365, 'y', 'year'],
	[60 * 24 * 30, 'mo', 'month'],
	[60 * 24, 'd', 'day'],
	[60, 'h', 'hour'],
	[1, 'm', 'minute']
];

function elapsed(timestamp: string | Date | null | undefined) {
	if (!timestamp) return null;
	const then = new Date(timestamp).getTime();
	if (Number.isNaN(then)) return null;
	const minutes = Math.floor((Date.now() - then) / 60000);
	for (const [per, short, long] of UNITS) {
		// >= 1, not != 0: a clock running ahead of ours falls through to just now
		const count = Math.floor(minutes / per);
		if (count >= 1) return { count, short, long };
	}
	return { count: 0, short: '', long: '' };
}

export function relativeTime(timestamp: string | Date | null | undefined): string {
	const e = elapsed(timestamp);
	if (!e) return 'never';
	return e.count ? `${e.count}${e.short} ago` : 'just now';
}

export function relativeTimeLong(timestamp: string | Date | null | undefined): string {
	const e = elapsed(timestamp);
	if (!e) return 'never';
	if (!e.count) return 'just now';
	return `${e.count} ${e.long}${e.count === 1 ? '' : 's'} ago`;
}

export function formatShortDate(date: string | Date): string {
	return new Date(date).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	});
}

export function formatMonthYear(date: string | Date): string {
	return new Date(date).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'short'
	});
}

export type ExpirationUrgency = 'expired' | 'critical' | 'warning' | 'healthy' | 'none';

export function getExpirationUrgency(expirationDate: string | null): ExpirationUrgency {
	if (!expirationDate) return 'none';

	const now = new Date();
	const expiry = new Date(expirationDate);
	const diffMs = expiry.getTime() - now.getTime();
	const diffDays = Math.floor(diffMs / MS_PER_DAY);

	if (diffDays < 0) return 'expired';
	if (diffDays <= 30) return 'critical';
	if (diffDays <= 180) return 'warning';
	return 'healthy';
}

export function formatExpirationLabel(expirationDate: string | null): string {
	if (!expirationDate) return '';

	const now = new Date();
	const expiry = new Date(expirationDate);
	const diffMs = expiry.getTime() - now.getTime();
	const diffDays = Math.floor(diffMs / MS_PER_DAY);

	if (diffDays < 0) {
		const absDays = Math.abs(diffDays);
		if (absDays < 30) return `Expired ${absDays}d ago`;
		const months = Math.floor(absDays / 30);
		return `Expired ${months}mo ago`;
	}
	if (diffDays === 0) return 'Expires today';
	if (diffDays <= 30) return `Expires in ${diffDays}d`;
	if (diffDays <= 365) {
		const months = Math.floor(diffDays / 30);
		return `Expires in ${months}mo`;
	}
	const years = Math.floor(diffDays / 365);
	const remainingMonths = Math.floor((diffDays % 365) / 30);
	if (remainingMonths > 0) return `Expires in ${years}y ${remainingMonths}mo`;
	return `Expires in ${years}y`;
}

export function getDomainAge(registrationDate: string | null): string {
	if (!registrationDate) return '';

	const now = new Date();
	const reg = new Date(registrationDate);
	const diffMs = now.getTime() - reg.getTime();
	const diffDays = Math.floor(diffMs / MS_PER_DAY);

	if (diffDays < 30) return `${diffDays} days old`;
	if (diffDays < 365) {
		const months = Math.floor(diffDays / 30);
		return `${months} ${months === 1 ? 'month' : 'months'} old`;
	}
	const years = Math.floor(diffDays / 365);
	const remainingMonths = Math.floor((diffDays % 365) / 30);
	if (remainingMonths > 0) return `${years}y ${remainingMonths}mo old`;
	return `${years} ${years === 1 ? 'year' : 'years'} old`;
}

export type FreshnessLevel = 'fresh' | 'recent' | 'aging' | 'stale' | 'never';

export interface FreshnessThresholds {
	fresh: number;
	recent: number;
	aging: number;
}

const DEFAULT_THRESHOLDS: FreshnessThresholds = {
	fresh: 24,
	recent: 72,
	aging: 168
};

export function getFreshnessLevel(
	timestamp: string | null | undefined,
	thresholds: FreshnessThresholds = DEFAULT_THRESHOLDS
): FreshnessLevel {
	if (!timestamp) return 'never';
	const hours = (Date.now() - new Date(timestamp).getTime()) / (1000 * 60 * 60);
	if (hours < thresholds.fresh) return 'fresh';
	if (hours < thresholds.recent) return 'recent';
	if (hours < thresholds.aging) return 'aging';
	return 'stale';
}

export interface FreshnessColors {
	dot: string;
	text: string;
	border: string;
}

const FRESHNESS_COLOR_MAP: Record<FreshnessLevel, FreshnessColors> = {
	fresh: {
		dot: 'bg-foreground',
		text: 'text-foreground',
		border: 'border-border'
	},
	recent: {
		dot: 'bg-muted-foreground',
		text: 'text-muted-foreground',
		border: 'border-border'
	},
	aging: {
		dot: 'bg-warning',
		text: 'text-warning',
		border: 'border-warning/20'
	},
	stale: {
		dot: 'bg-destructive',
		text: 'text-destructive',
		border: 'border-destructive/40'
	},
	never: {
		dot: 'bg-muted-foreground',
		text: 'text-muted-foreground',
		border: 'border-border'
	}
};

export function getFreshnessColors(level: FreshnessLevel): FreshnessColors {
	return FRESHNESS_COLOR_MAP[level];
}

export function getColorsForTimestamp(
	timestamp: string | null | undefined,
	thresholds?: FreshnessThresholds
): FreshnessColors {
	return getFreshnessColors(getFreshnessLevel(timestamp, thresholds));
}
