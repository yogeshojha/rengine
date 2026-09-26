import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { readPref, readRaw, removePref, writePref, writeRaw } from './storage';

class MemoryStorage implements Storage {
	private data = new Map<string, string>();
	get length() {
		return this.data.size;
	}
	clear() {
		this.data.clear();
	}
	getItem(key: string) {
		return this.data.get(key) ?? null;
	}
	key(index: number) {
		return [...this.data.keys()][index] ?? null;
	}
	removeItem(key: string) {
		this.data.delete(key);
	}
	setItem(key: string, value: string) {
		this.data.set(key, value);
	}
}

describe('storage', () => {
	let local: MemoryStorage;

	beforeEach(() => {
		local = new MemoryStorage();
		vi.stubGlobal('window', {});
		vi.stubGlobal('localStorage', local);
		vi.stubGlobal('sessionStorage', new MemoryStorage());
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('round-trips JSON and falls back on garbage', () => {
		writePref('rengine:test', { a: 1 });
		expect(readPref('rengine:test', null)).toEqual({ a: 1 });
		local.setItem('rengine:bad', '{nope');
		expect(readPref('rengine:bad', 'fallback')).toBe('fallback');
		expect(readPref('rengine:missing', 7)).toBe(7);
	});

	it('keeps session and local apart', () => {
		writePref('rengine:k', 1, 'session');
		expect(readPref('rengine:k', 0)).toBe(0);
		expect(readPref('rengine:k', 0, 'session')).toBe(1);
	});

	it('moves a value stored under a legacy key to its namespaced key', () => {
		local.setItem('activeProjectSlug', 'acme');
		expect(readRaw(STORAGE_KEYS.activeProjectSlug)).toBe('acme');
		expect(local.getItem(STORAGE_KEYS.activeProjectSlug)).toBe('acme');
		expect(local.getItem('activeProjectSlug')).toBeNull();
	});

	it('still answers a legacy value when storage is too full to move it', () => {
		local.setItem('activeProjectSlug', 'acme');
		local.setItem = () => {
			throw new Error('QuotaExceededError');
		};
		expect(readRaw(STORAGE_KEYS.activeProjectSlug)).toBe('acme');
		expect(local.getItem('activeProjectSlug')).toBe('acme');
	});

	it('reads legacy saved target views as JSON', () => {
		local.setItem('targets:views', JSON.stringify([{ name: 'a', query: 'b' }]));
		expect(readPref(STORAGE_KEYS.targetViews, [])).toEqual([{ name: 'a', query: 'b' }]);
	});

	it('removes the legacy key along with the new one', () => {
		local.setItem('activeProjectSlug', 'old');
		writeRaw(STORAGE_KEYS.activeProjectSlug, 'new');
		removePref(STORAGE_KEYS.activeProjectSlug);
		expect(readRaw(STORAGE_KEYS.activeProjectSlug)).toBeNull();
	});

	it('answers the fallback when storage throws', () => {
		vi.stubGlobal('localStorage', {
			getItem() {
				throw new Error('blocked');
			},
			setItem() {
				throw new Error('blocked');
			}
		});
		expect(readPref('rengine:x', 'fallback')).toBe('fallback');
		expect(() => writePref('rengine:x', 1)).not.toThrow();
	});

	it('answers the fallback when storage is absent', () => {
		vi.stubGlobal('localStorage', undefined);
		expect(readPref('rengine:x', 3)).toBe(3);
		expect(readRaw('rengine:x')).toBeNull();
	});

	it('treats the server as having no storage', () => {
		writePref('rengine:k', 1);
		vi.stubGlobal('window', undefined);
		expect(readPref('rengine:k', 0)).toBe(0);
	});
});
