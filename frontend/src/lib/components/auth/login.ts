import { STORAGE_KEYS } from '$lib/config/storage-keys';

export function markSessionExpired(): void {
	try {
		sessionStorage.setItem(STORAGE_KEYS.sessionExpired, '1');
	} catch {
		return;
	}
}

export function takeSessionExpired(): boolean {
	try {
		const marked = sessionStorage.getItem(STORAGE_KEYS.sessionExpired) !== null;
		sessionStorage.removeItem(STORAGE_KEYS.sessionExpired);
		return marked;
	} catch {
		return false;
	}
}
