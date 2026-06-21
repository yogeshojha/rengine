import { SvelteMap } from 'svelte/reactivity';

const overrides = new SvelteMap<string, string>();

export const breadcrumbStore = {
	get overrides() {
		return overrides;
	},

	set(segment: string, label: string) {
		overrides.set(segment, label);
	},

	remove(segment: string) {
		overrides.delete(segment);
	},

	getLabel(segment: string): string | undefined {
		return overrides.get(segment);
	},

	clear() {
		overrides.clear();
	}
};
