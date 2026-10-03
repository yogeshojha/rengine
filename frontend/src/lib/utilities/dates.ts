import { plural } from '$lib/utilities/strings';

export const MS_PER_DAY = 1000 * 60 * 60 * 24;

/** UTC calendar days from the day of `since` through today, as `YYYY-MM-DD`. */
export function utcDaysSince(since: string, now = Date.now()): string[] {
	const today = new Date(now).toISOString().slice(0, 10);
	const out: string[] = [];
	for (let t = Date.parse(`${since.slice(0, 10)}T00:00:00Z`); ; t += MS_PER_DAY) {
		const day = new Date(t).toISOString().slice(0, 10);
		if (day > today) break;
		out.push(day);
	}
	return out;
}

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

/** Time until a future moment, as "in 5h", or null once it has passed. */
export function untilTime(timestamp: string | Date | null | undefined): string | null {
	if (!timestamp) return null;
	const then = new Date(timestamp).getTime();
	if (Number.isNaN(then)) return null;
	const minutes = Math.floor((then - Date.now()) / 60000);
	if (minutes < 0) return null;
	for (const [per, short] of UNITS) {
		const count = Math.floor(minutes / per);
		if (count >= 1) return `in ${count}${short}`;
	}
	return 'in under a minute';
}

/** How long something has been running, as "3h" or "under a minute". */
export function uptime(timestamp: string | Date | null | undefined): string {
	const e = elapsed(timestamp);
	if (!e) return '';
	return e.count ? `${e.count}${e.short}` : 'under a minute';
}

export function formatShortDate(date: string | Date, utc = false): string {
	return new Date(date).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		...(utc ? { timeZone: 'UTC' } : {})
	});
}

export function formatDay(isoDate: string, weekday = false): string {
	return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString('en-US', {
		...(weekday ? { weekday: 'short' } : {}),
		month: 'short',
		day: 'numeric',
		timeZone: 'UTC'
	});
}

export function formatClock(date: string | Date, seconds = false): string {
	return new Date(date).toLocaleTimeString('en-US', {
		hour: 'numeric',
		minute: '2-digit',
		...(seconds ? { second: '2-digit' } : {})
	});
}

export function formatDateTime(date: string | Date): string {
	return new Date(date).toLocaleString('en-US', {
		month: 'short',
		day: 'numeric',
		hour: 'numeric',
		minute: '2-digit'
	});
}

export function formatMonthYear(date: string | Date, utc = false): string {
	return new Date(date).toLocaleDateString('en-US', {
		year: 'numeric',
		month: 'short',
		...(utc ? { timeZone: 'UTC' } : {})
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

	if (diffDays < 30) return `${plural(diffDays, 'day')} old`;
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

export function getFreshnessLevel(timestamp: string | null | undefined): FreshnessLevel {
	if (!timestamp) return 'never';
	const hours = (Date.now() - new Date(timestamp).getTime()) / (1000 * 60 * 60);
	if (hours < 24) return 'fresh';
	if (hours < 72) return 'recent';
	if (hours < 168) return 'aging';
	return 'stale';
}

export function viewerZone(): string {
	try {
		return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
	} catch {
		return 'UTC';
	}
}
