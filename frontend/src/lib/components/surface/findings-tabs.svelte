<script lang="ts">
	import { untrack } from 'svelte';
	import CountTabs, { type Tab } from '$lib/components/count-tabs.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { surfaceStore } from '$lib/stores/surface.svelte';
	import { FINDINGS_ROOT, FINDINGS_TABS, SURFACE, type FindingsTab } from '$lib/config/surface';
	import { findingsHref } from '$lib/config/routes';

	let { value }: { value: FindingsTab } = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let overview = $derived(surfaceStore.overview);

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => void surfaceStore.load(id));
	});

	let tabs = $derived<Tab[]>(
		FINDINGS_TABS.map((tab) => ({
			key: tab.key,
			label: tab.label,
			href: findingsHref(tab.key)
		}))
	);

	let counts = $derived.by(() => {
		if (!overview) return null;
		const out: Record<string, number> = {};
		for (const tab of FINDINGS_TABS) {
			out[tab.key] = tab.key === 'cve' ? overview.cves : (surfaceStore.total(tab.key) ?? 0);
		}
		return out;
	});

	let capped = $derived.by(() => {
		const out: Record<string, boolean> = {};
		for (const tab of FINDINGS_TABS) {
			if (tab.key === 'cve') continue;
			out[tab.key] = surfaceStore.coverage(tab.key)?.total_capped ?? false;
		}
		return out;
	});
</script>

<div class="space-y-3">
	<h1 class="text-2xl font-semibold tracking-tight">{SURFACE[FINDINGS_ROOT].label}</h1>
	<div class="border-b">
		<CountTabs {tabs} {value} {counts} {capped} />
	</div>
</div>
