<script lang="ts">
	import { untrack } from 'svelte';
	import FolderOpen from '@lucide/svelte/icons/folder-open';
	import Plus from '@lucide/svelte/icons/plus';
	import Play from '@lucide/svelte/icons/play';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import * as Empty from '$lib/components/ui/empty';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { dashboardStore } from '$lib/stores/dashboard.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import FirstRunPanel from '$lib/components/dashboard/first-run/first-run-panel.svelte';
	import Launcher from '$lib/components/dashboard/first-run/launcher.svelte';
	import StatStrip from '$lib/components/dashboard/stat-strip.svelte';
	import SurfaceTrend from '$lib/components/dashboard/surface-trend.svelte';
	import CoverageWidget from '$lib/components/dashboard/coverage-widget.svelte';
	import AttackQueue from '$lib/components/dashboard/attack-queue.svelte';
	import ExploitationWidget from '$lib/components/dashboard/exploitation-widget.svelte';
	import ExposuresWidget from '$lib/components/dashboard/exposures-widget.svelte';
	import ChangesFeed from '$lib/components/dashboard/changes-feed.svelte';
	import ServicesWidget from '$lib/components/dashboard/services-widget.svelte';
	import TechWidget from '$lib/components/dashboard/tech-widget.svelte';
	import HostingWidget from '$lib/components/dashboard/hosting-widget.svelte';
	import GeoWidget from '$lib/components/dashboard/geo-widget.svelte';
	import HygieneWidget from '$lib/components/dashboard/hygiene-widget.svelte';
	import MovementHeatmap from '$lib/components/dashboard/movement-heatmap.svelte';
	import SurfaceTreemap from '$lib/components/dashboard/surface-treemap.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { DASHBOARD_WINDOWS, type DashboardWindow, type QueueFilter } from '$lib/types/dashboard';

	const TICK_MS = 1000;

	let activeProject = $derived(projectsStore.activeProject);
	let overview = $derived(dashboardStore.overview);
	// first-run surface until a scan completes
	let firstRun = $derived(!!overview?.first_run && !overview.last_completed_at);
	let emptyProject = $derived(!!overview && overview.targets_total === 0 && !liveScans.hasLive);
	let addTargetOpen = $state(false);
	let launchOpen = $state(false);
	let launchTargetIds = $state<string[] | undefined>(undefined);
	let scheduleOpen = $state(false);
	let scheduleTargetIds = $state<string[]>([]);
	let now = $state(Date.now());
	let queueFilter = $state<QueueFilter>('all');

	let feed = $derived(dashboardStore.feed);
	let feedHasRows = $derived(
		!!feed &&
			(feed.vulns.total > 0 ||
				feed.exposures.total > 0 ||
				feed.services.total > 0 ||
				feed.endpoints.total > 0)
	);
	let hasServices = $derived((overview?.exposure.services ?? 0) > 0);
	let hasTech = $derived((dashboardStore.tech?.length ?? 0) > 0);
	let hasHosting = $derived((dashboardStore.hosting?.resolved ?? 0) > 0);
	let hasGeo = $derived((dashboardStore.ipFacets?.country.length ?? 0) > 0);
	let hasExposures = $derived((dashboardStore.exposures?.total ?? 0) > 0);
	let hasMovement = $derived((overview?.changes.length ?? 0) > 0);
	let hasTreemap = $derived(
		!!overview && overview.targets.some((t) => t.surface.some((s) => (s.value ?? 0) > 0))
	);
	let subline = $derived.by(() => {
		if (!overview || !activeProject) return '';
		const parts = [activeProject.name];
		parts.push(
			`${overview.targets_total.toLocaleString()} ${overview.targets_total === 1 ? 'target' : 'targets'}`
		);
		if (overview.last_completed_at)
			parts.push(`last run completed ${relativeTime(overview.last_completed_at)}`);
		return parts.join(' · ');
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

	function scanTargets(ids?: string[]) {
		launchTargetIds = ids;
		launchOpen = true;
	}
	function scheduleTargets(ids: string[]) {
		scheduleTargetIds = ids;
		scheduleOpen = true;
	}
</script>

<div class="flex flex-col gap-4">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="flex min-w-0 flex-col gap-1.5">
			<div class="flex items-baseline gap-2">
				<h1 class="text-lg font-semibold">Dashboard</h1>
				<span class="truncate text-sm text-muted-foreground">
					{subline || (activeProject?.name ?? 'Select a project')}
				</span>
			</div>
		</div>
		{#if activeProject && !firstRun && !emptyProject}
			<div class="flex flex-wrap items-center gap-2">
				<ToggleGroup.Root
					type="single"
					variant="outline"
					size="sm"
					value={dashboardStore.window}
					onValueChange={(v) => v && dashboardStore.setWindow(v as DashboardWindow)}
					aria-label="Change window"
				>
					{#each DASHBOARD_WINDOWS as w (w.key)}
						<ToggleGroup.Item value={w.key} class="px-2.5" aria-label={w.text}>
							{w.label}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
				<Button
					variant="outline"
					size="sm"
					onclick={() => dashboardStore.refresh()}
					disabled={dashboardStore.loading}
					aria-label="Refresh"
				>
					<RefreshCw class="size-4 {dashboardStore.loading ? 'animate-spin' : ''}" />
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
	{:else if firstRun}
		<FirstRunPanel {overview} readiness={dashboardStore.readiness} {now} />
	{:else if emptyProject}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<div class="px-5 py-5">
				<Launcher
					heading="No targets in this project"
					sub="Scanning a target adds it to this project."
				/>
			</div>
		</Card.Root>
	{:else}
		<StatStrip {overview} window={dashboardStore.window} />

		{#if overview}
			<div class="grid grid-cols-12 gap-4">
				{#if overview.runs_total > 0}
					<SurfaceTrend
						{overview}
						window={dashboardStore.window}
						class="col-span-12 {hasGeo ? 'xl:col-span-8' : ''}"
					/>
				{/if}
				{#if hasGeo}
					<GeoWidget
						countries={dashboardStore.ipFacets?.country ?? null}
						loading={dashboardStore.extrasLoading}
						class="col-span-12 lg:col-span-6 xl:col-span-4"
					/>
				{/if}

				{#if overview.risk.targets_scanned > 0 || overview.risk.total > 0}
					<AttackQueue
						{overview}
						window={dashboardStore.window}
						filter={queueFilter}
						onFilter={(f) => (queueFilter = f)}
						class="col-span-12 xl:col-span-8"
					/>
				{/if}
				<CoverageWidget
					{overview}
					window={dashboardStore.window}
					liveCount={liveScans.count}
					onScan={scanTargets}
					onSchedule={scheduleTargets}
					class="col-span-12 lg:col-span-6 xl:col-span-4"
				/>

				{#if dashboardStore.intel?.coverage?.findings}
					<ExploitationWidget
						intel={dashboardStore.intel}
						projectId={projectsStore.activeProject?.id ?? null}
						loading={dashboardStore.extrasLoading}
						class="col-span-12 lg:col-span-6 xl:col-span-4"
					/>
				{/if}
				{#if feedHasRows}
					<ChangesFeed {feed} class="col-span-12 lg:col-span-6 xl:col-span-4" />
				{/if}
				{#if hasServices}
					<ServicesWidget
						exposure={overview.exposure}
						class="col-span-12 lg:col-span-6 xl:col-span-4"
					/>
				{/if}
				{#if hasExposures}
					<ExposuresWidget
						page={dashboardStore.exposures}
						class="col-span-12 lg:col-span-6 xl:col-span-4"
					/>
				{/if}

				{#if hasHosting}
					<HostingWidget
						hosting={dashboardStore.hosting}
						networks={dashboardStore.ipFacets?.asn ?? null}
						loading={dashboardStore.extrasLoading}
						class="col-span-12 lg:col-span-6 xl:col-span-4"
					/>
				{/if}
				{#if hasTech}
					<TechWidget
						tech={dashboardStore.tech}
						loading={dashboardStore.extrasLoading}
						class="col-span-12 lg:col-span-6 xl:col-span-4"
					/>
				{/if}
				<HygieneWidget
					{overview}
					discovery={dashboardStore.discovery}
					class="col-span-12 lg:col-span-6 xl:col-span-4"
				/>

				{#if hasMovement}
					<MovementHeatmap
						{overview}
						window={dashboardStore.window}
						class="col-span-12 {hasTreemap ? 'xl:col-span-8' : ''}"
					/>
				{/if}
				{#if hasTreemap}
					<SurfaceTreemap {overview} class="col-span-12 {hasMovement ? 'xl:col-span-4' : ''}" />
				{/if}
			</div>
		{/if}
	{/if}
</div>

<AddTargetModal bind:open={addTargetOpen} />
<LaunchDialog bind:open={launchOpen} targetIds={launchTargetIds} />
<ScheduleModal bind:open={scheduleOpen} presetTargetIds={scheduleTargetIds} />
