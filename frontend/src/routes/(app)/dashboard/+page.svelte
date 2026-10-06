<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import FolderOpen from '@lucide/svelte/icons/folder-open';
	import Plus from '@lucide/svelte/icons/plus';
	import Play from '@lucide/svelte/icons/play';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { Button } from '$lib/components/ui/button';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { dashboardStore } from '$lib/stores/dashboard.svelte';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import FirstRunPanel from '$lib/components/dashboard/first-run/first-run-panel.svelte';
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
	import AiCell from '$lib/components/dashboard/ai-cell.svelte';
	import HostingCell from '$lib/components/dashboard/hosting-cell.svelte';
	import SharedCell from '$lib/components/dashboard/shared-cell.svelte';
	import ActivityCell from '$lib/components/dashboard/activity-cell.svelte';
	import CustomizePopover from '$lib/components/dashboard/customize-popover.svelte';
	import DashboardSkeleton from '$lib/components/dashboard/dashboard-skeleton.svelte';
	import HiddenTray from '$lib/components/dashboard/hidden-tray.svelte';
	import ScopeBar from '$lib/components/dashboard/scope-bar.svelte';
	import DashboardAsk from '$lib/components/ask/dashboard-ask.svelte';
	import {
		provideScopeLinks,
		scopeClause,
		withClause
	} from '$lib/components/dashboard/scope-links';
	import { scopeFromParams, scopeToParams } from '$lib/utilities/dashboard-scope';
	import { isScoped, type TargetScope } from '$lib/utilities/surface-scope';
	import { cappedPlural, plural } from '$lib/utilities/strings';
	import { packedSpans } from '$lib/utilities/bento';
	import { Severity } from '$lib/config/vulnerabilities';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import {
		DASHBOARD_SLICE_LABELS,
		DASHBOARD_WINDOWS,
		windowDays,
		type DashboardWindow
	} from '$lib/types/dashboard';

	const TICK_MS = 1000;
	const LIVE_REFRESH_MS = 30000;

	let activeProject = $derived(projectsStore.activeProject);
	let overview = $derived(dashboardStore.overview);
	let firstRun = $derived(!!overview?.first_run);
	let addTargetOpen = $state(false);
	let launchOpen = $state(false);
	let launchTargetIds = $state<string[] | undefined>(undefined);
	let scheduleOpen = $state(false);
	let scheduleTargetIds = $state<string[]>([]);
	let now = $state(Date.now());

	let urlScope = $derived(scopeFromParams(page.url.searchParams));
	let scope = $derived(dashboardStore.scope);
	let scoped = $derived(isScoped(scope));
	let clause = $derived(
		scoped && overview ? scopeClause(overview.targets.map((t) => t.value)) : ''
	);
	provideScopeLinks({
		get clause() {
			return clause;
		},
		get scope() {
			return scope;
		}
	});
	let win = $derived(dashboardStore.window);
	let days = $derived(windowDays(win));
	let extras = $derived(dashboardStore.extrasLoading);
	let programs = $derived(dashboardStore.programs);
	let notLoaded = $derived(
		dashboardStore.failedSlices.map((slice) => DASHBOARD_SLICE_LABELS[slice])
	);
	const show = (id: string) => dashboardLayout.visible(id);

	let riskOn = $derived(show('surface-risk'));
	let geoOn = $derived(
		show('geo') && (extras || (dashboardStore.ipFacets?.country.length ?? 0) > 0)
	);
	let changesOn = $derived(show('changes'));
	let inventoryOn = $derived(show('inventory'));

	const spansFor = (keys: (string | false)[], wide?: string): Record<string, string> => {
		const shown = keys.filter((k): k is string => !!k);
		const spans = packedSpans(shown.length, wide ? shown.indexOf(wide) : -1);
		return Object.fromEntries(shown.map((k, i) => [k, spans[i]]));
	};
	let findingsRow = $derived(
		spansFor(
			[
				show('findings-trend') && 'findings-trend',
				show('exploitation') &&
					(extras || !!dashboardStore.intel?.coverage?.findings) &&
					'exploitation',
				show('evidence') && !!overview?.risk.evidence.length && 'evidence'
			],
			'findings-trend'
		)
	);
	let programsRow = $derived(
		spansFor([
			show('programs') && (programs?.programs_total ?? 0) > 0 && 'programs',
			show('watches') && (programs?.watches.total ?? 0) > 0 && 'watches',
			show('connectors') && (programs?.browsing.connectors ?? 0) > 0 && 'connectors'
		])
	);
	let postureRow = $derived(
		spansFor([
			show('certs') && !!overview?.certs.buckets.some((b) => b.count > 0) && 'certs',
			show('hygiene') && (extras || (dashboardStore.hygiene?.evaluated ?? 0) > 0) && 'hygiene',
			show('domain-posture') &&
				(extras || (dashboardStore.posture?.evaluated ?? 0) > 0) &&
				'domain-posture',
			show('ownership') && 'ownership'
		])
	);
	let scanningRow = $derived(
		spansFor([
			show('runs') && (overview?.runs_total ?? 0) > 0 && 'runs',
			show('software') &&
				(extras || (dashboardStore.software?.facets.product.length ?? 0) > 0) &&
				'software'
		])
	);
	let compositionRow = $derived(
		spansFor([
			show('services') && (overview?.exposure.services ?? 0) > 0 && 'services',
			show('tech') && (extras || (dashboardStore.tech?.length ?? 0) > 0) && 'tech',
			show('ai') && (extras || (dashboardStore.ai?.found ?? 0) > 0) && 'ai',
			show('hosting') && (extras || (dashboardStore.hosting?.resolved ?? 0) > 0) && 'hosting',
			show('shared') && (extras || (dashboardStore.shared?.hubs.length ?? 0) > 0) && 'shared'
		])
	);

	let counts = $derived(
		dashboardStore.windowCounts?.window === win ? dashboardStore.windowCounts : null
	);
	let firstRuns = $derived(overview?.changes.filter((c) => c.first.length > 0).length ?? 0);
	let headline = $derived.by(() => {
		if (!counts) return null;
		const web = counts.new.find((c) => c.key === SurfaceDimension.WEB_ASSETS);
		const vulns = counts.new.find((c) => c.key === SurfaceDimension.VULNERABILITIES);
		if (!web || !vulns || (!web.count && !vulns.count)) return null;
		return {
			web,
			vulns,
			critical: counts.findings[Severity.CRITICAL] ?? 0,
			targets: counts.targets_with_new_web_assets
		};
	});

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];
	const headlineHref = (spec: typeof WEB, q: string) =>
		ROUTES.surface(spec.tab, { ...spec.rowView, [spec.queryParam]: withClause(clause, q) });

	let lastProject: string | undefined;
	$effect(() => {
		const pid = activeProject?.id;
		const next = urlScope;
		untrack(() => {
			if (!pid) return;
			if (lastProject && lastProject !== pid && isScoped(next)) {
				lastProject = pid;
				setScope({});
				return;
			}
			if (lastProject !== pid) void scanSchedulesStore.fetchSchedules(pid);
			lastProject = pid;
			dashboardStore.init(pid, next);
		});
	});

	function setScope(next: TargetScope) {
		const params = scopeToParams(page.url.searchParams, next);
		const qs = params.toString();
		void goto(qs ? `?${qs}` : page.url.pathname, { keepFocus: true, noScroll: true });
	}

	$effect(() => {
		if (liveScans.completedTick > 0) untrack(() => dashboardStore.refresh());
	});

	$effect(() => {
		if (!liveScans.hasLive) return;
		const iv = setInterval(() => (now = Date.now()), TICK_MS);
		const refresh = setInterval(() => dashboardStore.refresh(), LIVE_REFRESH_MS);
		return () => {
			clearInterval(iv);
			clearInterval(refresh);
		};
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

<svelte:head><title>{pageTitle(routeLabels.dashboard)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="flex min-w-0 flex-col gap-1.5">
			<span class="font-mono text-2xs tracking-[0.1em] text-muted-foreground uppercase">
				{activeProject?.name ??
					'Dashboard'}{#if overview}{` · ${plural(overview.targets_total, 'target', 'targets')} · ${days} days`}{/if}
			</span>
			{#if overview && !firstRun && headline}
				<h1 class="max-w-[34ch] text-2xl leading-tight font-semibold tracking-tight text-balance">
					{#if headline.critical}
						<a
							href={headlineHref(
								VULNS,
								`severity:${Severity.CRITICAL} and ${headline.vulns.query}`
							)}
							class="text-destructive hover:text-destructive/80"
							>{plural(headline.critical, 'critical finding', 'critical findings')}</a
						>
						and
					{/if}
					<a href={headlineHref(VULNS, headline.vulns.query)} class="hover:text-primary"
						>{cappedPlural(headline.vulns.count, headline.vulns.capped, 'finding')}</a
					>
					in {days} days.
					<span class="font-medium text-muted-foreground">
						<a href={headlineHref(WEB, headline.web.query)} class="hover:text-primary"
							>{cappedPlural(headline.web.count, headline.web.capped, 'new web asset')}</a
						>{headline.targets ? ` on ${plural(headline.targets, 'target', 'targets')}` : ''}.
					</span>
				</h1>
			{:else if overview && !firstRun && (counts || !dashboardStore.windowLoading)}
				<h1 class="max-w-[34ch] text-2xl leading-tight font-semibold tracking-tight text-balance">
					{plural(overview.runs_in_window, 'run', 'runs')} in {days} days.
					<span class="font-medium text-muted-foreground">
						{#if firstRuns}
							{plural(firstRuns, 'first run', 'first runs')}.
						{:else}
							No change.
						{/if}
					</span>
				</h1>
			{:else if overview && !firstRun}
				<Skeleton class="h-8 w-80 max-w-full" />
			{:else}
				<h1 class="text-2xl font-semibold tracking-tight">Dashboard</h1>
			{/if}
		</div>
		{#if activeProject && !firstRun}
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
				<Hint text="Refresh">
					{#snippet child(props)}
						<Button
							{...props}
							variant="outline"
							size="icon-sm"
							onclick={() => dashboardStore.refresh()}
							disabled={dashboardStore.loading}
							aria-label="Refresh"
						>
							<RefreshCw class="size-4 {dashboardStore.loading ? 'animate-spin' : ''}" />
						</Button>
					{/snippet}
				</Hint>
				<Button variant="outline" size="sm" onclick={() => (addTargetOpen = true)}>
					<Plus class="size-4" />
					Add target
				</Button>
				<Button
					size="sm"
					onclick={() => scanTargets(scoped ? overview?.targets.map((t) => t.id) : undefined)}
				>
					<Play class="size-4" />
					Start scan
				</Button>
			</div>
		{/if}
	</div>

	{#if activeProject && overview && !firstRun}
		<div class="flex flex-wrap items-center justify-between gap-2">
			<ScopeBar
				projectSlug={activeProject.slug}
				{scope}
				known={overview.targets}
				onChange={setScope}
			/>
			<DashboardAsk {scope} />
		</div>
	{/if}

	{#if !activeProject && projectsStore.hasFetched}
		<EmptyState
			icon={FolderOpen}
			title="No project selected"
			description="Select or create a project."
		/>
	{:else if dashboardStore.error && !overview}
		<EmptyState
			icon={TriangleAlert}
			title="Dashboard not loaded"
			description={dashboardStore.error}
		>
			<Button
				variant="outline"
				size="sm"
				onclick={() => dashboardStore.refresh()}
				disabled={dashboardStore.loading}
			>
				<RefreshCw class="size-4 {dashboardStore.loading ? 'animate-spin' : ''}" />
				Retry
			</Button>
		</EmptyState>
	{:else if firstRun}
		<FirstRunPanel readiness={dashboardStore.readiness} />
	{:else if overview}
		{#if notLoaded.length}
			<div
				class="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-dashed px-4 py-2.5 text-sm text-muted-foreground"
			>
				<TriangleAlert class="size-4 shrink-0 text-warning" strokeWidth={1.5} />
				<span>{notLoaded.join(', ')} not loaded.</span>
				<Button
					variant="outline"
					size="sm"
					class="ml-auto"
					onclick={() => dashboardStore.refresh()}
					disabled={dashboardStore.loading}
				>
					<RefreshCw class="size-4 {dashboardStore.loading ? 'animate-spin' : ''}" />
					Retry
				</Button>
			</div>
		{/if}

		<!-- estate -->
		<div class="grid grid-flow-row-dense grid-cols-12 overflow-hidden rounded-xl border bg-card">
			{#if riskOn}
				<SurfaceRiskCell
					data={dashboardStore.surfaceRisk}
					loading={extras}
					onScope={setScope}
					class="col-span-12 {geoOn ? 'xl:col-span-8' : ''}"
				/>
			{/if}
			{#if geoOn}
				<GeoCell
					countries={dashboardStore.ipFacets?.country ?? null}
					loading={extras}
					class="col-span-12 {inventoryOn ? 'lg:col-span-6' : ''} {riskOn
						? 'xl:col-span-4'
						: 'xl:col-span-12'}"
				/>
			{/if}
			{#if changesOn}
				<ChangesCell
					{overview}
					window={win}
					{counts}
					loading={dashboardStore.windowLoading}
					class="col-span-12 {inventoryOn ? 'xl:col-span-8' : ''}"
				/>
			{/if}
			{#if inventoryOn}
				<InventoryCell
					{overview}
					intel={dashboardStore.intel}
					{programs}
					{now}
					class="col-span-12 {geoOn ? 'lg:col-span-6' : ''} {changesOn
						? 'xl:col-span-4'
						: 'xl:col-span-12'}"
				/>
			{/if}
		</div>

		<!-- findings -->
		{#if overview.risk.total > 0 || overview.risk.targets_scanned > 0}
			<div class="overflow-hidden rounded-xl border bg-card">
				{#if show('board')}
					<div class="grid"><BoardCell risk={overview.risk} /></div>
				{/if}
				{#if Object.keys(findingsRow).length}
					<div class="grid grid-cols-12">
						{#if findingsRow['findings-trend']}
							<SeverityTrendCell
								{overview}
								window={win}
								{counts}
								loading={dashboardStore.windowLoading}
								class={findingsRow['findings-trend']}
							/>
						{/if}
						{#if findingsRow.exploitation}
							<ExploitationCell
								intel={dashboardStore.intel}
								changes={dashboardStore.changes}
								projectId={activeProject?.id ?? null}
								window={win}
								since={overview.since}
								loading={extras}
								class={findingsRow.exploitation}
							/>
						{/if}
						{#if findingsRow.evidence}
							<EvidenceCell risk={overview.risk} class={findingsRow.evidence} />
						{/if}
					</div>
				{/if}
				{#if show('exposures') && (extras || (dashboardStore.exposures?.summary.total ?? 0) > 0)}
					<div class="grid"><ExposuresCell page={dashboardStore.exposures} loading={extras} /></div>
				{/if}
			</div>
		{/if}

		<!-- programs (bug bounty) -->
		{#if programs && Object.keys(programsRow).length}
			<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
				{#if programsRow.programs}
					<ProgramsCell {programs} window={win} class={programsRow.programs} />
				{/if}
				{#if programsRow.watches}
					<WatchesCell
						watches={programs.watches}
						window={win}
						since={programs.since}
						class={programsRow.watches}
					/>
				{/if}
				{#if programsRow.connectors}
					<BrowsingCell
						browsing={programs.browsing}
						window={win}
						since={programs.since}
						class={programsRow.connectors}
					/>
				{/if}
			</div>
		{/if}

		<!-- posture (corporate) -->
		{#if Object.keys(postureRow).length}
			<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
				{#if postureRow.certs}
					<CertsCell
						buckets={overview.certs.buckets}
						expiringQuery={overview.certs.expiring.query}
						class={postureRow.certs}
					/>
				{/if}
				{#if postureRow.hygiene}
					<HygieneCell
						hygiene={dashboardStore.hygiene}
						loading={extras}
						class={postureRow.hygiene}
					/>
				{/if}
				{#if postureRow['domain-posture']}
					<DomainPostureCell
						summary={dashboardStore.posture}
						hosts={dashboardStore.postureHosts}
						loading={extras}
						class={postureRow['domain-posture']}
					/>
				{/if}
				{#if postureRow.ownership}
					<OwnershipCell
						{overview}
						discovery={dashboardStore.discovery}
						onSchedule={scheduleTargets}
						class={postureRow.ownership}
					/>
				{/if}
			</div>
		{/if}

		<!-- scanning + composition -->
		<div class="overflow-hidden rounded-xl border bg-card">
			{#if Object.keys(scanningRow).length}
				<div class="grid grid-cols-12">
					{#if scanningRow.runs}
						<RunsCell {overview} window={win} class={scanningRow.runs} />
					{/if}
					{#if scanningRow.software}
						<SoftwareCell
							software={dashboardStore.software}
							loading={extras}
							class={scanningRow.software}
						/>
					{/if}
				</div>
			{/if}
			{#if Object.keys(compositionRow).length}
				<div class="grid grid-cols-12">
					{#if compositionRow.services}
						<ServicesCell exposure={overview.exposure} class={compositionRow.services} />
					{/if}
					{#if compositionRow.tech}
						<TechCell tech={dashboardStore.tech} loading={extras} class={compositionRow.tech} />
					{/if}
					{#if compositionRow.ai}
						<AiCell ai={dashboardStore.ai} loading={extras} class={compositionRow.ai} />
					{/if}
					{#if compositionRow.hosting}
						<HostingCell
							hosting={dashboardStore.hosting}
							networks={dashboardStore.ipFacets?.asn ?? null}
							loading={extras}
							class={compositionRow.hosting}
						/>
					{/if}
					{#if compositionRow.shared}
						<SharedCell
							graph={dashboardStore.shared}
							loading={extras}
							class={compositionRow.shared}
						/>
					{/if}
				</div>
			{/if}
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
