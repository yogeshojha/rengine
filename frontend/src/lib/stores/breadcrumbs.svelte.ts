import { SvelteMap } from 'svelte/reactivity';

export interface Crumb {
	label: string;
	href: string;
}

const overrides = new SvelteMap<string, string | Crumb[]>();

export const breadcrumbStore = {
	set(segment: string, label: string) {
		overrides.set(segment, label);
	},

	setTrail(segment: string, crumbs: Crumb[]) {
		overrides.set(segment, crumbs);
	},

	remove(segment: string) {
		overrides.delete(segment);
	},

	getLabel(segment: string): string | undefined {
		const v = overrides.get(segment);
		return typeof v === 'string' ? v : undefined;
	},

	getTrail(segment: string): Crumb[] | undefined {
		const v = overrides.get(segment);
		return Array.isArray(v) ? v : undefined;
	},

	clear() {
		overrides.clear();
	}
};
