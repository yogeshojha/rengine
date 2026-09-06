<script lang="ts">
	import { untrack } from 'svelte';
	import FolderOpen from '@lucide/svelte/icons/folder-open';
	import Plus from '@lucide/svelte/icons/plus';
	import Play from '@lucide/svelte/icons/play';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import * as Empty from '$lib/components/ui/empty';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { dashboardStore } from '$lib/stores/dashboard.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import HeroPanel from '$lib/components/dashboard/hero-panel.svelte';
	import AttentionPanel, {
		type QueueFilter
	} from '$lib/components/dashboard/attention-panel.svelte';
	import VulnerabilityPanel from '$lib/components/dashboard/vulnerability-panel.svelte';
	import ChangesPanel, { type ChartMetric } from '$lib/components/dashboard/changes-panel.svelte';
	import ExposurePanel from '$lib/components/dashboard/exposure-panel.svelte';
	import { SurfaceDimension } from '$lib/config/surface';

	const TICK_MS = 1000;
	const SECTION = {
		vulns: 'dashboard-vulnerabilities',
		exposure: 'dashboard-exposure',
		changes: 'dashboard-changes'
	};

	let activeProject = $derived(projectsStore.activeProject);
	let overview = $derived(dashboardStore.overview);
	let addTargetOpen = $state(false);
	let launchOpen = $state(false);
	let launchTargetIds = $state<string[] | undefined>(undefined);
	let scheduleOpen = $state(false);
	let scheduleTargetIds = $state<string[]>([]);
	let now = $state(Date.now());
	let queueFilter = $state<QueueFilter>('all');
	let chartMetric = $state<ChartMetric | null>(null);
	const CHART_ORDER: ChartMetric[] = [
		SurfaceDimension.WEB_ASSETS,
		SurfaceDimension.SERVICES,
		SurfaceDimension.VULNERABILITIES,
		'runs'
	];
	// the chart opens on the first metric with data in the window
	let defaultMetric = $derived.by<ChartMetric>(() => {
		const days = overview ? overview.daily.slice(dashboardStore.window === '30d' ? -30 : -7) : [];
		for (const key of CHART_ORDER) {
			const total = days.reduce((n, d) => n + (key === 'runs' ? d.runs : (d.new[key] ?? 0)), 0);
			if (total > 0) return key;
		}
		return CHART_ORDER[0];
	});

	$effect(() => {
		const pid = activeProject?.id;
		untrack(() => {
			if (pid) dashboardStore.init(pid);
		});
	});

	$effect(() => {
		if (liveScans.completedTick > 0) untrack(() => dashboardStore.refresh());
	});

	$effect(() => {
		if (!liveScans.hasLive) return;
		const iv = setInterval(() => (now = Date.now()), TICK_MS);
		return () => clearInterval(iv);
	});

	function scrollTo(id: string) {
		document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
	}
	function openQueue(filter: QueueFilter) {
		queueFilter = filter;
		scrollTo(SECTION.vulns);
	}
	function showChanges(key: SurfaceDimension) {
		chartMetric =
			key === SurfaceDimension.ENDPOINTS || key === SurfaceDimension.IPS ? chartMetric : key;
		scrollTo(SECTION.changes);
	}
	function scanTargets(ids?: string[]) {
		launchTargetIds = ids;
		launchOpen = true;
	}
	function scheduleTargets(ids: string[]) {
		scheduleTargetIds = ids;
		scheduleOpen = true;
	}
</script>

<div class="flex flex-col gap-5">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex items-baseline gap-2">
			<h1 class="text-lg font-semibold">Dashboard</h1>
			<span class="text-sm text-muted-foreground">{activeProject?.name ?? 'Select a project'}</span>
		</div>
		{#if activeProject}
			<div class="flex items-center gap-2">
				<Button
					variant="outline"
					size="sm"
					onclick={() => dashboardStore.refresh()}
					disabled={dashboardStore.loading}
				>
					<RefreshCw class="size-4 {dashboardStore.loading ? 'animate-spin' : ''}" />
					Refresh
				</Button>
				<Button variant="outline" size="sm" onclick={() => (addTargetOpen = true)}>
					<Plus class="size-4" />
					Add target
				</Button>
				<Button size="sm" onclick={() => scanTargets()}>
					<Play class="size-4" />
					Start scan
				</Button>
			</div>
		{/if}
	</div>

	{#if !activeProject}
		<Empty.Root class="rounded-lg border border-dashed border-border py-16">
			<Empty.Header>
				<Empty.Media class="rounded-full bg-muted/30 p-3">
					<FolderOpen class="size-5 text-muted-foreground" strokeWidth={1.5} />
				</Empty.Media>
				<Empty.Title class="text-sm">No project selected</Empty.Title>
				<Empty.Description>Select or create a project to view its dashboard.</Empty.Description>
			</Empty.Header>
		</Empty.Root>
	{:else if dashboardStore.error && !overview}
		<Empty.Root class="rounded-lg border border-dashed border-destructive/40 py-12">
			<Empty.Header>
				<Empty.Media class="rounded-full bg-destructive/10 p-3">
					<TriangleAlert class="size-5 text-destructive" strokeWidth={1.5} />
				</Empty.Media>
				<Empty.Title class="text-sm">Dashboard could not be loaded</Empty.Title>
				<Empty.Description>{dashboardStore.error}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button
					variant="outline"
					onclick={() => dashboardStore.refresh()}
					disabled={dashboardStore.loading}
				>
					<RefreshCw class="size-4 {dashboardStore.loading ? 'animate-spin' : ''}" />
					Retry
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else}
		<HeroPanel
			{overview}
			loading={dashboardStore.loading}
			window={dashboardStore.window}
			{now}
			onWindow={(w) => dashboardStore.setWindow(w)}
			onChanges={showChanges}
			onScan={() => scanTargets()}
			onScanTargets={scanTargets}
			onAddTarget={() => (addTargetOpen = true)}
		/>

		<AttentionPanel
			{overview}
			discovery={dashboardStore.discovery}
			loading={dashboardStore.loading}
			onQueue={openQueue}
			onScanTargets={scanTargets}
			onSchedule={scheduleTargets}
			onExposure={() => scrollTo(SECTION.exposure)}
		/>

		{#if overview && overview.targets_total > 0}
			<div id={SECTION.vulns} class="scroll-mt-4">
				<VulnerabilityPanel
					{overview}
					window={dashboardStore.window}
					filter={queueFilter}
					onFilter={(f) => (queueFilter = f)}
				/>
			</div>
			<div id={SECTION.exposure} class="scroll-mt-4">
				<ExposurePanel exposure={overview.exposure} sensitive={overview.sensitive} />
			</div>
			{#if overview.runs_total > 0}
				<div id={SECTION.changes} class="scroll-mt-4">
					<ChangesPanel
						{overview}
						window={dashboardStore.window}
						metric={chartMetric ?? defaultMetric}
						onMetric={(m) => (chartMetric = m)}
					/>
				</div>
			{/if}
		{/if}
	{/if}
</div>

<AddTargetModal bind:open={addTargetOpen} />
<LaunchDialog bind:open={launchOpen} targetIds={launchTargetIds} />
<ScheduleModal bind:open={scheduleOpen} presetTargetIds={scheduleTargetIds} />
