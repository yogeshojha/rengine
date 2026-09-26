import { LEGACY_STORAGE_KEYS } from '$lib/config/storage-keys';

// Web storage throws in a private window or with site data blocked. On the
// server there is no window, and a Node global `localStorage` would be shared by
// every request, so storage counts as absent there. Every read here falls back
// and every write is best effort, so a preference that cannot persist never
// breaks the page.

export type StorageArea = 'local' | 'session';

function area(which: StorageArea): Storage | null {
	if (typeof window === 'undefined') return null;
	try {
		if (which === 'session') {
			return typeof sessionStorage === 'undefined' ? null : sessionStorage;
		}
		return typeof localStorage === 'undefined' ? null : localStorage;
	} catch {
		return null;
	}
}

/**
 * The stored string for `key`, or null. A key renamed in `LEGACY_STORAGE_KEYS`
 * still answers from its old name once, and the value moves to the new name.
 */
export function readRaw(key: string, which: StorageArea = 'local'): string | null {
	const store = area(which);
	if (!store) return null;
	try {
		const value = store.getItem(key);
		if (value !== null) return value;
		const legacy = LEGACY_STORAGE_KEYS[key];
		if (!legacy) return null;
		const old = store.getItem(legacy);
		if (old === null) return null;
		try {
			store.setItem(key, old);
			store.removeItem(legacy);
		} catch {
			// storage full or read-only: the old key stays, and is read again next time
		}
		return old;
	} catch {
		return null;
	}
}

export function writeRaw(key: string, value: string, which: StorageArea = 'local'): void {
	try {
		area(which)?.setItem(key, value);
	} catch {
		// storage unavailable or full
	}
}

/** Removes `key`, and its legacy name when it had one. */
export function removePref(key: string, which: StorageArea = 'local'): void {
	const store = area(which);
	if (!store) return;
	try {
		store.removeItem(key);
		const legacy = LEGACY_STORAGE_KEYS[key];
		if (legacy) store.removeItem(legacy);
	} catch {
		// storage unavailable
	}
}

/** The JSON value stored under `key`, or the fallback when absent or unparsable. */
export function readPref<T>(key: string, fallback: T, which: StorageArea = 'local'): T {
	const raw = readRaw(key, which);
	if (!raw) return fallback;
	try {
		return JSON.parse(raw) as T;
	} catch {
		return fallback;
	}
}

export function writePref(key: string, value: unknown, which: StorageArea = 'local'): void {
	let raw: string;
	try {
		raw = JSON.stringify(value);
	} catch {
		return;
	}
	writeRaw(key, raw, which);
}
