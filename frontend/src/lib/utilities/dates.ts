export const MS_PER_DAY = 1000 * 60 * 60 * 24;

export const formatDate = (dateString: string) => {
	const date = new Date(dateString);
	return date.toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'long',
		day: 'numeric'
	});
};

export function formatDistanceToNow(date: string | Date): string {
	const now = new Date();
	const past = new Date(date);
	const diffInSeconds = Math.floor((now.getTime() - past.getTime()) / 1000);

	if (diffInSeconds < 60) {
		return 'just now';
	}

	const diffInMinutes = Math.floor(diffInSeconds / 60);
	if (diffInMinutes < 60) {
		return `${diffInMinutes} ${diffInMinutes === 1 ? 'minute' : 'minutes'}`;
	}

	const diffInHours = Math.floor(diffInMinutes / 60);
	if (diffInHours < 24) {
		return `${diffInHours} ${diffInHours === 1 ? 'hour' : 'hours'}`;
	}

	const diffInDays = Math.floor(diffInHours / 24);
	if (diffInDays < 30) {
		return `${diffInDays} ${diffInDays === 1 ? 'day' : 'days'}`;
	}

	const diffInMonths = Math.floor(diffInDays / 30);
	if (diffInMonths < 12) {
		return `${diffInMonths} ${diffInMonths === 1 ? 'month' : 'months'}`;
	}

	const diffInYears = Math.floor(diffInMonths / 12);
	return `${diffInYears} ${diffInYears === 1 ? 'year' : 'years'}`;
}

export function relativeTime(timestamp: string | null | undefined): string {
	if (!timestamp) return 'never';
	const diffMs = Date.now() - new Date(timestamp).getTime();
	const minutes = Math.floor(diffMs / 60000);
	if (minutes < 1) return 'just now';
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	if (days < 30) return `${days}d ago`;
	const months = Math.floor(days / 30);
	return `${months}mo ago`;
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
