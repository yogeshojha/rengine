<script lang="ts">
	import { untrack } from 'svelte';
	import CorrelationTab from '$lib/components/scans/results/correlation/correlation-tab.svelte';
	import ScopeStrip from '$lib/components/surface/scope-strip.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { surfaceStore } from '$lib/stores/surface.svelte';
	import { SurfaceDimension } from '$lib/config/surface';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { goto } from '$app/navigation';

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let coverage = $derived(surfaceStore.coverage(SurfaceDimension.WEB_ASSETS));

	let launchIds = $state<string[]>([]);
	let launchOpen = $state(false);

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => void surfaceStore.load(id));
	});

	function afterLaunch() {
		launchOpen = false;
		if (projectId) void surfaceStore.load(projectId, true);
	}
</script>

<div class="space-y-6">
	<div class="flex flex-col gap-1">
		<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.correlation}</h1>
		<p class="text-sm text-muted-foreground">Identities two or more web assets carry</p>
	</div>

	<div class="overflow-hidden rounded-xl border bg-card">
		<ScopeStrip
			{coverage}
			onScanUncovered={(ids) => {
				launchIds = ids;
				launchOpen = true;
			}}
		/>
	</div>

	{#key projectId}
		<CorrelationTab
			scanId=""
			projectWide
			{projectId}
			onTab={(_tab, filter) => goto(ROUTES.surface('web-assets', filter ? { q: filter } : {}))}
		/>
	{/key}
</div>

<LaunchDialog bind:open={launchOpen} targetIds={launchIds} onClose={afterLaunch} />
