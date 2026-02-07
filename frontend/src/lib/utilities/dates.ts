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

export function formatDateTime(date: string | Date): string {
	return new Date(date).toLocaleString('en-US', {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
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
	const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

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
	const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

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
	const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

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
