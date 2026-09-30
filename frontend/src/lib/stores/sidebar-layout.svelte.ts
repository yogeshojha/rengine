import { browser } from '$app/environment';
import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { auth } from '$lib/stores/auth.svelte';
import { SvelteMap, SvelteSet } from 'svelte/reactivity';

function key(userId: string) {
	return `${STORAGE_KEYS.sidebarHidden}:${userId}`;
}

function read(userId: string): string[] {
	if (!browser) return [];
	try {
		const parsed = JSON.parse(localStorage.getItem(key(userId)) ?? '[]');
		return Array.isArray(parsed) ? parsed.filter((v) => typeof v === 'string') : [];
	} catch {
		return [];
	}
}

function write(userId: string, ids: Iterable<string>) {
	if (!browser) return;
	try {
		localStorage.setItem(key(userId), JSON.stringify([...ids]));
	} catch {
		// storage unavailable
	}
}

function createSidebarLayout() {
	const byUser = new SvelteMap<string, SvelteSet<string>>();

	const userId = () => auth.user?.id ?? '';
	function hiddenSet(): SvelteSet<string> {
		const id = userId();
		let set = byUser.get(id);
		if (!set) {
			set = new SvelteSet(read(id));
			byUser.set(id, set);
		}
		return set;
	}

	return {
		load() {
			hiddenSet();
		},
		hidden(id: string): boolean {
			return byUser.get(userId())?.has(id) ?? false;
		},
		set(id: string, visible: boolean) {
			const set = hiddenSet();
			if (visible) set.delete(id);
			else set.add(id);
			write(userId(), set);
		},
		reset() {
			const set = hiddenSet();
			set.clear();
			write(userId(), set);
		},
		get customized(): boolean {
			return (byUser.get(userId())?.size ?? 0) > 0;
		}
	};
}

export const sidebarLayout = createSidebarLayout();
