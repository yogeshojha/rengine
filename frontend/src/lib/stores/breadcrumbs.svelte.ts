/**
 * Breadcrumb override store.
 *
 * Pages with dynamic route segments (e.g. [id]) call this to replace
 * the raw UUID in breadcrumbs with a human-readable label.
 *
 * Usage:
 *   breadcrumbStore.set($page.params.id, target.target_value);
 *   onDestroy(() => breadcrumbStore.remove($page.params.id));
 */

let overrides = $state<Map<string, string>>(new Map());

export const breadcrumbStore = {
	get overrides() {
		return overrides;
	},

	set(segment: string, label: string) {
		const next = new Map(overrides);
		next.set(segment, label);
		overrides = next;
	},

	remove(segment: string) {
		const next = new Map(overrides);
		next.delete(segment);
		overrides = next;
	},

	getLabel(segment: string): string | undefined {
		return overrides.get(segment);
	},

	clear() {
		overrides = new Map();
	},
};
