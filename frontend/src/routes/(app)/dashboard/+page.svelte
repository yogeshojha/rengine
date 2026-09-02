<script lang="ts">
	import { untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { activityFeed } from '$lib/stores/activity-feed.svelte';
	import { dashboardStore } from '$lib/stores/dashboard.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ActivityLog } from '$lib/types/activity';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import ActivityTimeline from '$lib/components/activity/activity-timeline.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import AttackSurfaceDelta from '$lib/components/dashboard/attack-surface-delta.svelte';
	import NeedsAttention from '$lib/components/dashboard/needs-attention.svelte';
	import TargetsByTypeDonut from '$lib/components/dashboard/targets-by-type-donut.svelte';
	import Boxes from '@lucide/svelte/icons/boxes';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Hourglass from '@lucide/svelte/icons/hourglass';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import FolderOpen from '@lucide/svelte/icons/folder-open';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import type { SignalFilter } from '$lib/utilities/target-signals';
	import { TargetType } from '$lib/types/target';
	import { ROUTES } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';
	import { ACTIVITY_TICK_MS } from '$lib/constants';

	let activeProject = $derived(projectsStore.activeProject);
	let addTargetOpen = $state(false);

	$effect(() => {
		const slug = activeProject?.slug;
		untrack(() => {
			if (slug) targetsStore.fetchAll(slug);
		});
	});

	$effect(() => {
		const pid = activeProject?.id;
		untrack(() => {
			if (pid) {
				activityFeed.reset();
				activityFeed.load(pid, 1);
			}
		});
	});

	$effect(() => {
		const pid = activeProject?.id;
		untrack(() => {
			if (pid) dashboardStore.init(pid);
		});
	});

	$effect(() => {
		if (liveScans.completedTick > 0) dashboardStore.refresh();
	});

	$effect(() => {
		const pid = activeProject?.id;
		if (!pid) return;
		return sseStore.on<ActivityLog>(SSEChannel.project(pid), SSEEventType.ACTIVITY, (d) =>
			activityFeed.ingest(d)
		);
	});

	$effect(() => {
		const iv = setInterval(() => activityFeed.bumpTick(), ACTIVITY_TICK_MS);
		return () => clearInterval(iv);
	});

	let summary = $derived(targetsStore.signalSummary);

	function retryStats() {
		const slug = activeProject?.slug;
		if (slug) targetsStore.fetchAll(slug, undefined, true);
	}

	function refresh() {
		const slug = activeProject?.slug;
		const pid = activeProject?.id;
		if (slug) targetsStore.refresh();
		if (pid) {
			activityFeed.load(pid, 1);
			dashboardStore.refresh();
		}
	}

	interface Kpi {
		signal: SignalFilter | null;
		label: string;
		value: number;
		icon: IconComponent;
		accent: string;
	}

	let kpis = $derived<Kpi[]>([
		{
			signal: 'attention',
			label: 'Needs attention',
			value: summary.attention,
			icon: TriangleAlert,
			accent: 'text-destructive'
		},
		{
			signal: 'expiring',
			label: 'Expiring',
			value: summary.expiring,
			icon: CalendarClock,
			accent: 'text-warning'
		},
		{
			signal: null,
			label: 'Total targets',
			value: summary.total,
			icon: Boxes,
			accent: 'text-foreground'
		},
		{
			signal: 'awaiting',
			label: 'Awaiting enrichment',
			value: summary.awaiting,
			icon: Hourglass,
			accent: 'text-chart-1'
		},
		{
			signal: 'enriched',
			label: 'Enriched',
			value: summary.enriched,
			icon: ShieldCheck,
			accent: 'text-foreground'
		}
	]);

	let breakdown = $derived(
		[
			{ type: TargetType.DOMAIN, count: targetsStore.counts.domain },
			{ type: TargetType.IP, count: targetsStore.counts.ip },
			{ type: TargetType.IP_RANGE, count: targetsStore.counts.ip_range },
			{ type: TargetType.ASN, count: targetsStore.counts.asn },
			{ type: TargetType.URL, count: targetsStore.counts.url }
		].filter((b) => b.count > 0)
	);

	function openSignal(signal: SignalFilter | null) {
		goto(signal ? `${ROUTES.targets}?signal=${signal}` : ROUTES.targets);
	}

	function openType(type: TargetType) {
		goto(`${ROUTES.targets}?type=${type}`);
	}
</script>

<div class="space-y-6">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="text-lg font-semibold">Dashboard</h1>
			<p class="text-sm text-muted-foreground">
				{activeProject?.name ?? 'Select a project'}
			</p>
		</div>
		{#if activeProject}
			<div class="flex items-center gap-2">
				<Button variant="outline" size="sm" onclick={refresh} disabled={targetsStore.isLoading}>
					<RefreshCw class="h-4 w-4 {targetsStore.isLoading ? 'animate-spin' : ''}" />
					Refresh
				</Button>
				<Button size="sm" onclick={() => (addTargetOpen = true)}>
					<Plus class="h-4 w-4" />
					Add target
				</Button>
			</div>
		{/if}
	</div>

	{#if projectsStore.isLoading && !activeProject}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
			{#each { length: 5 } as _, i (i)}
				<Skeleton class="h-[88px] rounded-xl" />
			{/each}
		</div>
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
			<Skeleton class="h-64 rounded-xl lg:col-span-2" />
			<Skeleton class="h-64 rounded-xl" />
		</div>
	{:else if activeProject}
		{#if targetsStore.error && !targetsStore.hasFetched}
			<Empty.Root class="rounded-lg border border-dashed border-destructive/40 py-12">
				<Empty.Header>
					<Empty.Media class="rounded-full bg-destructive/10 p-3">
						<TriangleAlert class="h-5 w-5 text-destructive" strokeWidth={1.5} />
					</Empty.Media>
					<Empty.Title class="text-sm">Couldn't load dashboard</Empty.Title>
					<Empty.Description>{targetsStore.error}</Empty.Description>
				</Empty.Header>
				<Empty.Content>
					<Button variant="outline" onclick={retryStats} disabled={targetsStore.isLoading}>
						<RefreshCw class="h-4 w-4 {targetsStore.isLoading ? 'animate-spin' : ''}" />
						Retry
					</Button>
				</Empty.Content>
			</Empty.Root>
		{:else}
			<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
				{#each kpis as kpi (kpi.label)}
					<Tooltip.Root>
						<Tooltip.Trigger>
							{#snippet child({ props })}
								<button
									{...props}
									type="button"
									onclick={() => openSignal(kpi.signal)}
									aria-label={kpi.signal ? `View ${kpi.label} targets` : 'View all targets'}
									class="w-full text-left"
								>
									<Card.Root class="h-full transition-colors hover:bg-muted/40">
										<Card.Content class="flex items-center gap-3 px-4 py-3">
											<kpi.icon class="h-4 w-4 shrink-0 {kpi.accent}" />
											<div class="min-w-0">
												<div class="text-lg font-semibold leading-none tabular-nums">
													{#if targetsStore.isLoading && !targetsStore.hasFetched}
														<Skeleton class="h-5 w-8 rounded" />
													{:else}
														{kpi.value}
													{/if}
												</div>
												<div class="mt-1 truncate text-[11px] text-muted-foreground">
													{kpi.label}
												</div>
											</div>
										</Card.Content>
									</Card.Root>
								</button>
							{/snippet}
						</Tooltip.Trigger>
						<Tooltip.Content>
							<p class="text-xs">
								{kpi.signal ? `Filter targets by ${kpi.label.toLowerCase()}` : 'View all targets'}
							</p>
						</Tooltip.Content>
					</Tooltip.Root>
				{/each}
			</div>

			<AttackSurfaceDelta
				changes={dashboardStore.changes}
				window={dashboardStore.changeWindow}
				onWindow={(w) => dashboardStore.setChangeWindow(w)}
			/>

			<NeedsAttention
				signals={dashboardStore.signals}
				loading={dashboardStore.loadingSignals}
				error={dashboardStore.signalsError}
				onRetry={() => dashboardStore.retrySignals()}
			/>

			<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
				<Card.Root>
					<Card.Header>
						<Card.Title class="text-sm">Attack surface</Card.Title>
						<Card.Description>By asset type across {summary.total} targets</Card.Description>
					</Card.Header>
					<Card.Content>
						{#if !targetsStore.hasFetched}
							<div class="flex justify-center py-6">
								<Skeleton class="h-[170px] w-[170px] rounded-full" />
							</div>
						{:else if summary.total === 0}
							<Empty.Root class="border-none py-8">
								<Empty.Header>
									<Empty.Media class="rounded-full bg-muted/30 p-3">
										<Boxes class="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
									</Empty.Media>
									<Empty.Title class="text-sm">No targets yet</Empty.Title>
									<Empty.Description
										>Add a target to start mapping your attack surface.</Empty.Description
									>
								</Empty.Header>
								<Empty.Content>
									<Button onclick={() => (addTargetOpen = true)}>
										<Plus class="h-4 w-4" />
										Add target
									</Button>
								</Empty.Content>
							</Empty.Root>
						{:else}
							<TargetsByTypeDonut {breakdown} total={summary.total} onSelect={openType} />
						{/if}
					</Card.Content>
				</Card.Root>

				<Card.Root class="flex flex-col lg:col-span-2">
					<Card.Header class="flex flex-row items-center justify-between gap-2 space-y-0">
						<div class="flex items-center gap-2">
							<Card.Title class="text-sm">Recent activity</Card.Title>
							{#if activityFeed.isLive}
								<span class="flex items-center gap-1 text-[10px] text-muted-foreground">
									<span class="h-1.5 w-1.5 animate-pulse rounded-full bg-foreground"></span>
									Live
								</span>
							{/if}
						</div>
						<Button
							variant="link"
							size="sm"
							class="h-auto p-0 text-xs"
							onclick={() => activityFeed.setOpen(true)}
						>
							View all
							<ArrowRight class="h-3 w-3" />
						</Button>
					</Card.Header>
					<Card.Content class="min-h-0 flex-1 p-0">
						<ScrollArea class="h-[360px]">
							<div class="px-4 pb-4">
								<ActivityTimeline
									dayGroups={activityFeed.days}
									targetGroups={activityFeed.targetGroups}
									grouping={activityFeed.grouping}
									newEventIds={activityFeed.freshIds}
									runningIds={activityFeed.runningIds}
									tick={activityFeed.tick}
									isLoading={activityFeed.initialLoad}
									isEmpty={!activityFeed.initialLoad && activityFeed.filtered.length === 0}
								/>
							</div>
						</ScrollArea>
					</Card.Content>
				</Card.Root>
			</div>
		{/if}
	{:else}
		<Empty.Root class="rounded-lg border border-dashed border-border py-16">
			<Empty.Header>
				<Empty.Media class="rounded-full bg-muted/30 p-3">
					<FolderOpen class="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
				</Empty.Media>
				<Empty.Title class="text-sm">No project selected</Empty.Title>
				<Empty.Description>Select or create a project to view its dashboard.</Empty.Description>
			</Empty.Header>
		</Empty.Root>
	{/if}
</div>

<AddTargetModal bind:open={addTargetOpen} />
