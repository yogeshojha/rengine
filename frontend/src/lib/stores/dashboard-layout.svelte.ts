import { browser } from '$app/environment';
import { STORAGE_KEYS } from '$lib/config/storage-keys';
import {
	DASHBOARD_WIDGETS,
	widgetAvailable,
	widgetDefaultOn,
	widgetSpec,
	type DashboardWidgetSpec
} from '$lib/config/dashboard-widgets';
import { coerceInstanceMode, InstanceMode } from '$lib/config/capabilities';
import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
import { SvelteMap, SvelteSet } from 'svelte/reactivity';

interface Stored {
	hidden: string[];
	shown: string[];
}

function key(mode: InstanceMode) {
	return `${STORAGE_KEYS.dashboardWidgets}:${mode}`;
}

function read(mode: InstanceMode): Stored {
	if (!browser) return { hidden: [], shown: [] };
	try {
		const raw = localStorage.getItem(key(mode));
		if (!raw) return { hidden: [], shown: [] };
		const parsed = JSON.parse(raw) as Partial<Stored>;
		return {
			hidden: Array.isArray(parsed.hidden) ? parsed.hidden : [],
			shown: Array.isArray(parsed.shown) ? parsed.shown : []
		};
	} catch {
		return { hidden: [], shown: [] };
	}
}

function write(mode: InstanceMode, value: Stored) {
	if (!browser) return;
	try {
		localStorage.setItem(key(mode), JSON.stringify(value));
	} catch {
		// storage unavailable
	}
}

function createDashboardLayout() {
	const hidden = new SvelteMap<InstanceMode, SvelteSet<string>>();
	const shown = new SvelteMap<InstanceMode, SvelteSet<string>>();
	for (const m of [InstanceMode.BugBounty, InstanceMode.Corporate]) {
		const stored = read(m);
		hidden.set(m, new SvelteSet(stored.hidden));
		shown.set(m, new SvelteSet(stored.shown));
	}

	function ensure(mode: InstanceMode) {
		return { hidden: hidden.get(mode)!, shown: shown.get(mode)! };
	}

	function persist(mode: InstanceMode) {
		const sets = ensure(mode);
		write(mode, { hidden: [...sets.hidden], shown: [...sets.shown] });
	}

	const mode = () => coerceInstanceMode(capabilitiesStore.mode);

	return {
		get mode() {
			return mode();
		},
		available(spec: DashboardWidgetSpec): boolean {
			return widgetAvailable(spec, capabilitiesStore.capabilities);
		},
		visible(id: string): boolean {
			const spec = widgetSpec(id);
			if (!spec) return false;
			const m = mode();
			if (!this.available(spec)) return false;
			const sets = ensure(m);
			if (sets.hidden.has(id)) return false;
			if (sets.shown.has(id)) return true;
			return widgetDefaultOn(spec, m);
		},
		hide(id: string) {
			const m = mode();
			const sets = ensure(m);
			sets.hidden.add(id);
			sets.shown.delete(id);
			persist(m);
		},
		show(id: string) {
			const m = mode();
			const sets = ensure(m);
			sets.hidden.delete(id);
			const spec = widgetSpec(id);
			if (spec && !widgetDefaultOn(spec, m)) sets.shown.add(id);
			persist(m);
		},
		reset() {
			const m = mode();
			const sets = ensure(m);
			sets.hidden.clear();
			sets.shown.clear();
			persist(m);
		},
		get hiddenWidgets(): DashboardWidgetSpec[] {
			const m = mode();
			const sets = ensure(m);
			return DASHBOARD_WIDGETS.filter(
				(w) => this.available(w) && sets.hidden.has(w.id) && widgetDefaultOn(w, m)
			);
		},
		get customized(): boolean {
			const sets = ensure(mode());
			return sets.hidden.size > 0 || sets.shown.size > 0;
		}
	};
}

export const dashboardLayout = createDashboardLayout();
