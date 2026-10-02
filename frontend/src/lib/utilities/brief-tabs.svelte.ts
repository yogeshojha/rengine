import { SvelteMap } from 'svelte/reactivity';

export interface BriefTabs<T extends string> {
	of(id: string): T;
	set(id: string, tab: T): void;
	close(id: string): void;
}

export function briefTabs<T extends string>(first: T): BriefTabs<T> {
	const tabs = new SvelteMap<string, T>();
	return {
		of: (id) => tabs.get(id) ?? first,
		set: (id, tab) => {
			tabs.set(id, tab);
		},
		close: (id) => {
			tabs.delete(id);
		}
	};
}
