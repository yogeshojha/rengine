<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
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
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import FirstRunPanel from '$lib/components/dashboard/first-run/first-run-panel.svelte';
	import Launcher from '$lib/components/dashboard/first-run/launcher.svelte';
	import SurfaceRiskCell from '$lib/components/dashboard/surface-risk-cell.svelte';
	import InventoryCell from '$lib/components/dashboard/inventory-cell.svelte';
	import ChangesCell from '$lib/components/dashboard/changes-cell.svelte';
	import GeoCell from '$lib/components/dashboard/geo-cell.svelte';
	import BoardCell from '$lib/components/dashboard/board-cell.svelte';
	import SeverityTrendCell from '$lib/components/dashboard/severity-trend-cell.svelte';
	import ExploitationCell from '$lib/components/dashboard/exploitation-cell.svelte';
	import EvidenceCell from '$lib/components/dashboard/evidence-cell.svelte';
	import ExposuresCell from '$lib/components/dashboard/exposures-cell.svelte';
	import ProgramsCell from '$lib/components/dashboard/programs-cell.svelte';
	import WatchesCell from '$lib/components/dashboard/watches-cell.svelte';
	import BrowsingCell from '$lib/components/dashboard/browsing-cell.svelte';
	import CertsCell from '$lib/components/dashboard/certs-cell.svelte';
	import HygieneCell from '$lib/components/dashboard/hygiene-cell.svelte';
	import DomainPostureCell from '$lib/components/dashboard/domain-posture-cell.svelte';
	import OwnershipCell from '$lib/components/dashboard/ownership-cell.svelte';
	import RunsCell from '$lib/components/dashboard/runs-cell.svelte';
	import SoftwareCell from '$lib/components/dashboard/software-cell.svelte';
	import ServicesCell from '$lib/components/dashboard/services-cell.svelte';
	import TechCell from '$lib/components/dashboard/tech-cell.svelte';
	import HostingCell from '$lib/components/dashboard/hosting-cell.svelte';
	import SharedCell from '$lib/components/dashboard/shared-cell.svelte';
	import ActivityCell from '$lib/components/dashboard/activity-cell.svelte';
	import CustomizePopover from '$lib/components/dashboard/customize-popover.svelte';
	import DashboardSkeleton from '$lib/components/dashboard/dashboard-skeleton.svelte';
	import HiddenTray from '$lib/components/dashboard/hidden-tray.svelte';
	import {
		DASHBOARD_SLICE_LABELS,
		DASHBOARD_WINDOWS,
		windowDays,
		type DashboardWindow
	} from '$lib/types/dashboard';

	const TICK_MS = 1000;

	let activeProject = $derived(projectsStore.activeProject);
	let overview = $derived(dashboardStore.overview);
	let firstRun = $derived(!!overview?.first_run && !overview.last_completed_at);
	let emptyProject = $derived(!!overview && overview.targets_total === 0 && !liveScans.hasLive);
	let addTargetOpen = $state(false);
	let launchOpen = $state(false);
	let launchTargetIds = $state<string[] | undefined>(undefined);
	let scheduleOpen = $state(false);
	let scheduleTargetIds = $state<string[]>([]);
	let now = $state(Date.now());

	let win = $derived(dashboardStore.window);
	let days = $derived(windowDays(win));
	let extras = $derived(dashboardStore.extrasLoading);
	let programs = $derived(dashboardStore.programs);
	let notLoaded = $derived(
		dashboardStore.failedSlices.map((slice) => DASHBOARD_SLICE_LABELS[slice])
	);
	const show = (id: string) => dashboardLayout.visible(id);

	let headline = $derived.by(() => {
		if (!overview) return null;
		const recent = overview.daily.slice(-days);
		const sum = (pick: (d: (typeof recent)[number]) => number) =>
			recent.reduce((n, d) => n + pick(d), 0);
		const findings = sum((d) => Object.values(d.findings).reduce((a, b) => a + b, 0));
		const critical = sum((d) => d.findings.critical ?? 0);
		const web = sum((d) => d.new.web_assets ?? 0);
		const targets = new Set(
			overview.changes.filter((c) => (c.new.web_assets ?? 0) > 0).map((c) => c.target_id)
		).size;
		const firsts = overview.changes.filter((c) => c.first.length > 0).length;
		return { findings, critical, web, targets, firsts, runs: overview.runs_in_window };
	});

	$effect(() => {
		const pid = activeProject?.id;
		untrack(() => {
			if (pid) {
				dashboardStore.init(pid);
				void scanSchedulesStore.fetchSchedules(pid);
			}
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
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
</script>

<svelte:head><title>{routeLabels.dashboard} · reNgine</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-4">
		<div class="flex min-w-0 flex-col gap-1.5">
			<span class="font-mono text-2xs tracking-[0.1em] text-muted-foreground uppercase">
				{activeProject?.name ?? 'Dashboard'}{#if overview}
					· {plural(overview.targets_total, 'target', 'targets')} · {days} days{/if}
			</span>
			{#if headline && !firstRun && !emptyProject && !headline.findings && !headline.web}
				<h1 class="max-w-[34ch] text-2xl leading-tight font-semibold tracking-tight text-balance">
					{plural(headline.runs, 'run', 'runs')} in {days} days.
					<span class="font-medium text-muted-foreground">
						{#if headline.firsts}
							{plural(headline.firsts, 'first run', 'first runs')}.
						{:else}
							No change.
						{/if}
					</span>
				</h1>
			{:else if headline && !firstRun && !emptyProject}
				<h1 class="max-w-[34ch] text-2xl leading-tight font-semibold tracking-tight text-balance">
					{#if headline.critical}
						<span class="text-destructive"
							>{plural(headline.critical, 'critical finding', 'critical findings')}</span
						>
						and
					{/if}
					{plural(headline.findings, 'finding', 'findings')} in {days} days.
					<span class="font-medium text-muted-foreground">
						{plural(headline.web, 'new web asset', 'new web assets')}{headline.targets
							? ` on ${plural(headline.targets, 'target', 'targets')}`
							: ''}.
					</span>
				</h1>
			{:else}
				<h1 class="text-lg font-semibold">Dashboard</h1>
			{/if}
		</div>
		{#if activeProject && !firstRun && !emptyProject}
			<div class="flex flex-wrap items-center gap-2">
				<ToggleGroup.Root
					type="single"
					variant="outline"
					size="sm"
					value={win}
					onValueChange={(v) => v && dashboardStore.setWindow(v as DashboardWindow)}
					aria-label="Window"
				>
					{#each DASHBOARD_WINDOWS as w (w.key)}
						<ToggleGroup.Item value={w.key} class="px-2.5" aria-label={w.text}>
							{w.label}
						</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
				<CustomizePopover />
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

	{#if !activeProject && projectsStore.hasFetched}
		<Empty.Root class="rounded-lg border border-dashed border-border py-16">
			<Empty.Header>
				<Empty.Media class="rounded-full bg-muted/30 p-3">
					<FolderOpen class="size-5 text-muted-foreground" strokeWidth={1.5} />
				</Empty.Media>
				<Empty.Title class="text-sm">No project selected</Empty.Title>
				<Empty.Description>Select or create a project.</Empty.Description>
			</Empty.Header>
		</Empty.Root>
	{:else if dashboardStore.error && !overview}
		<Empty.Root class="rounded-lg border border-dashed border-destructive/40 py-12">
			<Empty.Header>
				<Empty.Media class="rounded-full bg-destructive/10 p-3">
					<TriangleAlert class="size-5 text-destructive" strokeWidth={1.5} />
				</Empty.Media>
				<Empty.Title class="text-sm">Dashboard not loaded</Empty.Title>
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
				<Launcher heading="No targets in this project" sub="Add a target or start a scan." />
			</div>
		</Card.Root>
	{:else if overview}
		{#if notLoaded.length}
			<div
				class="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-dashed px-4 py-2.5 text-sm text-muted-foreground"
			>
				<TriangleAlert class="size-4 shrink-0 text-warning" strokeWidth={1.5} />
				<span>{notLoaded.join(', ')} did not load.</span>
				<Button
					variant="outline"
					size="sm"
					class="ml-auto"
					onclick={() => dashboardStore.refresh()}
					disabled={dashboardStore.loading}
				>
					<RefreshCw class="size-3.5 {dashboardStore.loading ? 'animate-spin' : ''}" />
					Retry
				</Button>
			</div>
		{/if}

		<!-- estate -->
		<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
			{#if show('surface-risk')}
				<SurfaceRiskCell
					data={dashboardStore.surfaceRisk}
					loading={extras}
					class="col-span-12 xl:col-span-8"
				/>
			{/if}
			{#if show('geo') && (extras || (dashboardStore.ipFacets?.country.length ?? 0) > 0)}
				<GeoCell
					countries={dashboardStore.ipFacets?.country ?? null}
					loading={extras}
					class="col-span-12 lg:col-span-6 xl:col-span-4"
				/>
			{/if}
			{#if show('changes')}
				<ChangesCell {overview} window={win} class="col-span-12 xl:col-span-8" />
			{/if}
			{#if show('inventory')}
				<InventoryCell
					{overview}
					intel={dashboardStore.intel}
					{programs}
					{now}
					class="col-span-12 lg:col-span-6 xl:col-span-4"
				/>
			{/if}
		</div>

		<!-- findings -->
		{#if overview.risk.total > 0 || overview.risk.targets_scanned > 0}
			<div class="overflow-hidden rounded-xl border bg-card">
				{#if show('board')}
					<div class="grid"><BoardCell risk={overview.risk} /></div>
				{/if}
				<div class="grid grid-cols-[repeat(auto-fit,minmax(16rem,1fr))]">
					{#if show('findings-trend')}
						<SeverityTrendCell {overview} window={win} class="xl:col-span-2" />
					{/if}
					{#if show('exploitation') && (extras || dashboardStore.intel?.coverage?.findings)}
						<ExploitationCell
							intel={dashboardStore.intel}
							changes={dashboardStore.changes}
							projectId={activeProject?.id ?? null}
							window={win}
							loading={extras}
						/>
					{/if}
					{#if show('evidence') && overview.risk.evidence.length}
						<EvidenceCell risk={overview.risk} />
					{/if}
				</div>
				{#if show('exposures') && (extras || (dashboardStore.exposures?.summary.total ?? 0) > 0)}
					<div class="grid"><ExposuresCell page={dashboardStore.exposures} loading={extras} /></div>
				{/if}
			</div>
		{/if}

		<!-- programs (bug bounty) -->
		{#if programs && (show('programs') || show('watches') || show('connectors'))}
			<div
				class="grid grid-cols-[repeat(auto-fit,minmax(20rem,1fr))] overflow-hidden rounded-xl border bg-card"
			>
				{#if show('programs') && programs.programs_total > 0}
					<ProgramsCell {programs} window={win} />
				{/if}
				{#if show('watches') && programs.watches.total > 0}
					<WatchesCell watches={programs.watches} window={win} />
				{/if}
				{#if show('connectors') && programs.browsing.connectors > 0}
					<BrowsingCell browsing={programs.browsing} window={win} />
				{/if}
			</div>
		{/if}

		<!-- posture (corporate) -->
		{#if show('certs') || show('hygiene') || show('domain-posture') || show('ownership')}
			<div
				class="grid grid-cols-[repeat(auto-fit,minmax(18rem,1fr))] overflow-hidden rounded-xl border bg-card"
			>
				{#if show('certs') && overview.certs.buckets.some((b) => b.count > 0)}
					<CertsCell
						buckets={overview.certs.buckets}
						expiringQuery={overview.certs.expiring.query}
					/>
				{/if}
				{#if show('hygiene') && (extras || (dashboardStore.hygiene?.evaluated ?? 0) > 0)}
					<HygieneCell hygiene={dashboardStore.hygiene} loading={extras} />
				{/if}
				{#if show('domain-posture') && (extras || (dashboardStore.posture?.evaluated ?? 0) > 0)}
					<DomainPostureCell
						summary={dashboardStore.posture}
						hosts={dashboardStore.postureHosts}
						loading={extras}
					/>
				{/if}
				{#if show('ownership')}
					<OwnershipCell
						{overview}
						discovery={dashboardStore.discovery}
						onSchedule={scheduleTargets}
					/>
				{/if}
			</div>
		{/if}

		<!-- scanning + composition -->
		<div class="overflow-hidden rounded-xl border bg-card">
			<div class="grid grid-cols-[repeat(auto-fit,minmax(22rem,1fr))]">
				{#if show('runs') && overview.runs_total > 0}
					<RunsCell {overview} window={win} />
				{/if}
				{#if show('software') && (extras || (dashboardStore.software?.facets.product.length ?? 0) > 0)}
					<SoftwareCell software={dashboardStore.software} loading={extras} />
				{/if}
			</div>
			<div class="grid grid-cols-[repeat(auto-fit,minmax(16rem,1fr))]">
				{#if show('services') && overview.exposure.services > 0}
					<ServicesCell exposure={overview.exposure} />
				{/if}
				{#if show('tech') && (extras || (dashboardStore.tech?.length ?? 0) > 0)}
					<TechCell tech={dashboardStore.tech} loading={extras} />
				{/if}
				{#if show('hosting') && (extras || (dashboardStore.hosting?.resolved ?? 0) > 0)}
					<HostingCell
						hosting={dashboardStore.hosting}
						networks={dashboardStore.ipFacets?.asn ?? null}
						loading={extras}
					/>
				{/if}
				{#if show('shared') && (extras || (dashboardStore.shared?.hubs.length ?? 0) > 0)}
					<SharedCell graph={dashboardStore.shared} loading={extras} />
				{/if}
			</div>
			{#if show('activity')}
				<div class="grid">
					<ActivityCell activity={dashboardStore.activity} loading={extras} />
				</div>
			{/if}
		</div>

		<HiddenTray />
	{:else}
		<DashboardSkeleton />
	{/if}
</div>

<AddTargetModal bind:open={addTargetOpen} />
<LaunchDialog bind:open={launchOpen} targetIds={launchTargetIds} />
<ScheduleModal bind:open={scheduleOpen} presetTargetIds={scheduleTargetIds} />
