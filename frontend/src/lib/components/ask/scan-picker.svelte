<script lang="ts">
	import { untrack } from 'svelte';
	import ScanLine from '@lucide/svelte/icons/scan-line';
	import ScopePicker, { type PickerItem } from '$lib/components/dashboard/scope-picker.svelte';
	import { estateApi } from '$lib/api/ask';
	import { formatDateTime } from '$lib/utilities/dates';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import { SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import type { ScanScope, ScanStatus } from '$lib/types/scan';
	import type { EstateScanOption } from '$lib/types/ask';
	import type { TargetScope } from '$lib/utilities/surface-scope';

	interface Props {
		projectId: string;
		scope: TargetScope;
		selected: string | null;
		onChange: (id: string | null, label: string | null) => void;
	}

	let { projectId, scope, selected, onChange }: Props = $props();

	const FOCUSED: ScanScope = 'focused';

	let options = $state<EstateScanOption[]>([]);
	let loading = $state(false);
	let search = '';
	let timer: ReturnType<typeof setTimeout> | null = null;
	let generation = 0;

	function when(at: string | null): string {
		return at ? formatDateTime(at) : '';
	}

	function label(o: EstateScanOption): string {
		const status = o.status as ScanStatus;
		const notes = [
			o.scope === FOCUSED ? 'focused' : '',
			status === 'completed' ? '' : (SCAN_STATUS_LABEL[status] ?? o.status).toLowerCase()
		].filter(Boolean);
		return [o.target, o.engine, when(o.at), ...notes].join(' · ');
	}

	let items = $derived<PickerItem[]>(options.map((o) => ({ id: o.id, label: label(o) })));

	async function load() {
		if (!projectId) return;
		const mine = ++generation;
		loading = true;
		try {
			const found = await estateApi.scans(projectId, scope, search);
			if (mine === generation) options = found;
		} catch {
			if (mine === generation) options = [];
		} finally {
			if (mine === generation) loading = false;
		}
	}

	$effect(() => () => {
		if (timer) clearTimeout(timer);
	});

	$effect(() => {
		void projectId;
		void $state.snapshot(scope);
		untrack(() => void load());
	});

	function onSearch(q: string) {
		search = q;
		if (timer) clearTimeout(timer);
		timer = setTimeout(() => void load(), SEARCH_DEBOUNCE_MS);
	}

	function pick(ids: string[]) {
		const id = ids[0] ?? null;
		const found = options.find((o) => o.id === id);
		onChange(id, found ? label(found) : null);
	}
</script>

<ScopePicker
	label="Scan"
	icon={ScanLine}
	{items}
	selected={selected ? [selected] : []}
	labelOf={(id) => {
		const found = options.find((o) => o.id === id);
		return found ? `${found.target} · ${when(found.at)}` : 'One scan';
	}}
	{loading}
	placeholder="Search scans"
	{onSearch}
	onChange={pick}
/>
