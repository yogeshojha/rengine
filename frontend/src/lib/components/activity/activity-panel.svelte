<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { activityScope } from '$lib/stores/activity-scope.svelte';
	import {
		activityFeed,
		FILTERS,
		FILTER_LABELS,
		type ActivityFilter
	} from '$lib/stores/activity-feed.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import { ACTIVITY_TICK_MS, NOW_TICK_MS } from '$lib/constants';
	import { ROUTES } from '$lib/config/routes';
	import type { ActivityLog } from '$lib/types/activity';
	import type { ScanRead } from '$lib/types/scan';
	import ActivityTimeline from './activity-timeline.svelte';
	import LiveScanCard from '$lib/components/scans/live-scan-card.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import { Toggle } from '$lib/components/ui/toggle/index.js';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Layers from '@lucide/svelte/icons/layers';
	import Pin from '@lucide/svelte/icons/pin';
	import PinOff from '@lucide/svelte/icons/pin-off';
	import Search from '@lucide/svelte/icons/search';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import X from '@lucide/svelte/icons/x';

	const PANEL_W = 360;
	const MAX_CARDS = 4;
	const sidebar = useSidebar();

	let projectId = $derived(projectsStore.activeProject?.id);
	let panelEl = $state<HTMLElement | null>(null);
	let sentinelEl = $state<HTMLDivElement | null>(null);
	let scrollEl = $state<HTMLDivElement | null>(null);
	let scrollTop = $state(0);

	let docked = $derived(activityFeed.pinned && !sidebar.isMobile);
	let scopedToTarget = $derived(!!activityFeed.targetId && activityFeed.scopeMode === 'current');
	let grouping = $derived(scopedToTarget ? 'timeline' : activityFeed.grouping);
	let showJump = $derived(scrollTop > 80 && activityFeed.freshIds.size > 0);
	let runningOpen = $state(true);
	let visibleScans = $derived(liveScans.scans.slice(0, MAX_CARDS));
	let overflow = $derived(liveScans.count - MAX_CARDS);

	let cancelTarget = $state<ScanRead | null>(null);
	let cancelling = $state(false);
	let rescanOpen = $state(false);
	let rescanTargetId = $state<string | undefined>(undefined);

	function rescan(targetId: string) {
		rescanTargetId = targetId;
		rescanOpen = true;
	}
	function onRescanClose() {
		rescanOpen = false;
		rescanTargetId = undefined;
		liveScans.refresh();
	}

	let connection = $derived.by((): { label: string; variant: BadgeVariant; dot: string } => {
		if (sseStore.isConnected) return { label: 'Live', variant: 'success', dot: 'bg-success' };
		if (sseStore.isReconnecting)
			return { label: 'Reconnecting', variant: 'warning', dot: 'bg-warning animate-pulse' };
		if (sseStore.connectionState === 'connecting')
			return { label: 'Connecting', variant: 'warning', dot: 'bg-warning animate-pulse' };
		return { label: 'Offline', variant: 'outline', dot: 'bg-muted-foreground/50' };
	});

	let now = $state(Date.now());
	$effect(() => {
		if (!liveScans.hasLive || !activityFeed.open) return;
		const t = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		return () => clearInterval(t);
	});

	$effect(() => {
		if (liveScans.hasLive) engineCatalogStore.fetch();
	});

	$effect(() => {
		const pid = projectId;
		untrack(() => {
			if (pid) {
				activityFeed.reset();
				activityFeed.load(pid, 1);
			}
		});
	});

	$effect(() => {
		if (!projectId) return;
		return sseStore.on<ActivityLog>(SSEChannel.project(projectId), SSEEventType.ACTIVITY, (d) =>
			activityFeed.ingest(d)
		);
	});

	$effect(() => {
		activityFeed.setTargetId(activityScope.targetId);
	});

	$effect(() => {
		const iv = setInterval(() => activityFeed.bumpTick(), ACTIVITY_TICK_MS);
		return () => clearInterval(iv);
	});

	$effect(() => {
		if (!sentinelEl) return;
		const observer = new IntersectionObserver(
			(entries) => {
				if (
					entries[0]?.isIntersecting &&
					activityFeed.hasMore &&
					!activityFeed.loading &&
					projectId
				) {
					activityFeed.load(projectId, activityFeed.page + 1);
				}
			},
			{ threshold: 0 }
		);
		observer.observe(sentinelEl);
		return () => observer.disconnect();
	});

	$effect(() => {
		const el = scrollEl;
		if (!el) return;
		const onScroll = () => (scrollTop = el.scrollTop);
		el.addEventListener('scroll', onScroll, { passive: true });
		return () => el.removeEventListener('scroll', onScroll);
	});

	function onWindowPointerDown(e: PointerEvent) {
		if (!activityFeed.open || docked) return;
		const t = e.target as HTMLElement;
		if (panelEl?.contains(t)) return;
		if (t.closest('[data-activity-glance]')) return;
		if (t.closest('[data-slot=alert-dialog-content]')) return;
		if (t.closest('[data-slot=dialog-content]')) return;
		activityFeed.setOpen(false);
	}

	function jumpToLive() {
		scrollEl?.scrollTo({ top: 0, behavior: 'smooth' });
	}

	async function confirmCancel() {
		const scan = cancelTarget;
		if (!scan) return;
		cancelling = true;
		const ok = await liveScans.cancel(scan);
		cancelling = false;
		cancelTarget = null;
		if (ok) toast.success(`Cancelling scan of ${scan.execution_config.target_value}`);
		else toast.error("Couldn't cancel scan — try again");
	}
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape' && activityFeed.open && !docked) activityFeed.setOpen(false);
	}}
	onpointerdown={onWindowPointerDown}
/>

<aside
	bind:this={panelEl}
	aria-label="Activity"
	aria-hidden={!activityFeed.open}
	inert={!activityFeed.open}
	class="flex flex-col border-l border-border bg-background {docked
		? 'relative z-10 shrink-0'
		: `absolute inset-y-0 right-0 z-30 shadow-2xl transition-transform duration-300 ease-out ${activityFeed.open ? 'translate-x-0' : 'translate-x-full'}`}"
	style="width: min({PANEL_W}px, 100vw)"
>
	<div class="flex shrink-0 items-center justify-between gap-2 px-3 py-2.5">
		<div class="flex min-w-0 items-center gap-2">
			<span class="text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
				Activity
			</span>

			<Badge variant={connection.variant} class="h-5 gap-1 px-1.5 text-[10px]">
				<span class="size-1.5 rounded-full {connection.dot}"></span>
				{connection.label}
			</Badge>

			{#if liveScans.hasLive}
				<Badge variant="info" class="h-5 gap-1 px-1.5 text-[10px] tabular-nums">
					<Spinner class="size-2.5" />
					{liveScans.count} running
				</Badge>
			{/if}

			{#if activityFeed.targetId}
				<Tabs.Root
					value={activityFeed.scopeMode}
					onValueChange={(v) => activityFeed.setScopeMode(v as 'current' | 'project')}
				>
					<Tabs.List class="h-6">
						<Tabs.Trigger value="current" class="h-4 px-2 text-[10px]">Current</Tabs.Trigger>
						<Tabs.Trigger value="project" class="h-4 px-2 text-[10px]">Project</Tabs.Trigger>
					</Tabs.List>
				</Tabs.Root>
			{/if}
		</div>

		<div class="flex shrink-0 items-center">
			{#if !sidebar.isMobile}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								onclick={() => activityFeed.setPinned(!activityFeed.pinned)}
								aria-label={activityFeed.pinned ? 'Unpin panel' : 'Pin panel'}
								aria-pressed={activityFeed.pinned}
								class="size-6 {activityFeed.pinned
									? 'text-foreground'
									: 'text-muted-foreground hover:text-foreground'}"
							>
								{#if activityFeed.pinned}
									<PinOff class="size-3.5" />
								{:else}
									<Pin class="size-3.5" />
								{/if}
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="bottom">
						{activityFeed.pinned ? 'Unpin' : 'Pin open beside the page'}
					</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			<Button
				variant="ghost"
				size="icon-sm"
				onclick={() => activityFeed.setOpen(false)}
				aria-label="Close"
				class="size-6 text-muted-foreground hover:text-foreground"
			>
				<X class="size-3.5" />
			</Button>
		</div>
	</div>

	{#if liveScans.hasLive}
		<Collapsible.Root bind:open={runningOpen} class="shrink-0 px-3 pb-2">
			<Collapsible.Trigger
				class="flex w-full items-center justify-between rounded-md px-1 py-1 text-[10px] font-semibold tracking-[0.08em] text-info uppercase transition-colors hover:bg-info/10"
			>
				<span class="flex items-center gap-1.5">
					<span class="relative flex size-1.5">
						<span
							class="absolute inline-flex size-full animate-ping rounded-full bg-info opacity-75"
						></span>
						<span class="relative inline-flex size-1.5 rounded-full bg-info"></span>
					</span>
					Running now
					<span class="font-mono tabular-nums opacity-70">{liveScans.count}</span>
				</span>
				<ChevronDown
					class="size-3 transition-transform duration-150 {runningOpen ? '' : '-rotate-90'}"
				/>
			</Collapsible.Trigger>
			<Collapsible.Content>
				<div class="mt-1 space-y-1.5">
					{#each visibleScans as scan (scan.id)}
						<LiveScanCard
							{scan}
							run={liveScans.runFor(scan.id)}
							catalog={engineCatalogStore.stages}
							previousDuration={liveScans.previousDuration(scan.id)}
							{now}
							onNavigate={() => {
								if (!docked) activityFeed.setOpen(false);
							}}
							onCancel={(s) => (cancelTarget = s)}
						/>
					{/each}
					{#if overflow > 0}
						<a
							href={ROUTES.scans}
							class="inline-flex items-center gap-1 px-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
						>
							+{overflow} more running
							<ArrowRight class="size-3" />
						</a>
					{/if}
				</div>
			</Collapsible.Content>
		</Collapsible.Root>
	{/if}

	<div class="px-3 pb-2">
		<div class="relative">
			<Search class="absolute top-1/2 left-2 size-3 -translate-y-1/2 text-muted-foreground" />
			<Input
				value={activityFeed.search}
				oninput={(e) => activityFeed.setSearch(e.currentTarget.value)}
				placeholder="Search activity…"
				class="h-7 border-border bg-muted/30 pr-7 pl-7 text-[11px] transition-colors focus:border-primary/40 focus:bg-background"
			/>
			{#if activityFeed.search}
				<button
					type="button"
					aria-label="Clear search"
					onclick={() => activityFeed.setSearch('')}
					class="absolute top-1/2 right-1.5 -translate-y-1/2 text-muted-foreground hover:text-foreground"
				>
					<X class="size-3" />
				</button>
			{/if}
		</div>
	</div>

	<div class="flex shrink-0 flex-wrap items-center gap-1 px-3 pb-2">
		{#each FILTERS as f (f)}
			{@const n = activityFeed.counts[f] ?? 0}
			{#if f === 'all' || n > 0}
				<button
					type="button"
					aria-pressed={activityFeed.filter === f}
					class="rounded-full px-2.5 py-[3px] text-[10px] font-medium transition-colors {activityFeed.filter ===
					f
						? 'bg-accent text-foreground ring-1 ring-border'
						: 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'}"
					onclick={() => activityFeed.setFilter(f as ActivityFilter)}
				>
					{FILTER_LABELS[f]}
					<span class="ml-0.5 font-mono text-[9px] tabular-nums opacity-60">{n}</span>
				</button>
			{/if}
		{/each}

		<div class="ml-auto flex items-center gap-0.5">
			{#if !scopedToTarget}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Toggle
								{...props}
								size="sm"
								pressed={activityFeed.grouping === 'target'}
								onPressedChange={(v) => activityFeed.setGrouping(v ? 'target' : 'timeline')}
								aria-label="Group by target"
								class="h-6 min-w-6 rounded-full px-1.5 text-muted-foreground data-[state=on]:text-foreground"
							>
								<Layers class="size-3" />
							</Toggle>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="bottom">
						{activityFeed.grouping === 'target' ? 'Grouped by target' : 'Group by target'}
					</Tooltip.Content>
				</Tooltip.Root>
			{/if}
			<Hint text="Errors only">
				{#snippet child(props)}
					<button
						{...props}
						type="button"
						aria-pressed={activityFeed.errorsOnly}
						onclick={() => activityFeed.toggleErrorsOnly()}
						class="inline-flex items-center gap-1 rounded-full px-2 py-[3px] text-[10px] font-medium transition-colors {activityFeed.errorsOnly
							? 'bg-destructive/10 text-destructive ring-1 ring-destructive/40'
							: activityFeed.errorCount > 0
								? 'text-destructive/80 hover:bg-destructive/10 hover:text-destructive'
								: 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'}"
					>
						<ShieldAlert class="size-3" />
						Errors
						{#if activityFeed.errorCount > 0}
							<span class="font-mono text-[9px] tabular-nums opacity-80">
								{activityFeed.errorCount}
							</span>
						{/if}
					</button>
				{/snippet}
			</Hint>
		</div>
	</div>

	<Separator />

	<div class="relative min-h-0 flex-1">
		{#if showJump}
			<button
				type="button"
				onclick={jumpToLive}
				class="absolute top-2 left-1/2 z-20 inline-flex -translate-x-1/2 items-center gap-1 rounded-full border border-primary/20 bg-primary px-2.5 py-1 text-[10px] font-semibold text-primary-foreground shadow-lg transition-transform hover:scale-105"
			>
				<ArrowUp class="size-3" />
				{activityFeed.freshIds.size} new
			</button>
		{/if}

		<ScrollArea class="h-full" bind:viewportRef={scrollEl}>
			<div class="px-3 pt-2 pb-4">
				<ActivityTimeline
					dayGroups={activityFeed.days}
					targetGroups={activityFeed.targetGroups}
					{grouping}
					newEventIds={activityFeed.freshIds}
					runningIds={activityFeed.runningIds}
					tick={activityFeed.tick}
					isLoading={activityFeed.initialLoad}
					isEmpty={!activityFeed.initialLoad && activityFeed.filtered.length === 0}
					onRescan={rescan}
				/>

				{#if activityFeed.loading && !activityFeed.initialLoad}
					<div class="flex justify-center py-3">
						<Spinner class="size-3.5 text-muted-foreground" />
					</div>
				{/if}

				{#if activityFeed.hasMore && !activityFeed.initialLoad}
					<div bind:this={sentinelEl} class="h-1"></div>
				{/if}
			</div>
		</ScrollArea>

		<div
			class="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-background to-transparent"
		></div>
	</div>
</aside>

<LaunchDialog bind:open={rescanOpen} targetId={rescanTargetId} onClose={onRescanClose} />

<ConfirmDialog
	open={!!cancelTarget}
	title="Cancel this scan?"
	description="The scan will stop queuing further work and be marked cancelled."
	confirmLabel="Cancel scan"
	cancelLabel="Keep running"
	destructive
	loading={cancelling}
	loadingLabel="Cancelling…"
	onOpenChange={(o) => {
		if (!o) cancelTarget = null;
	}}
	onConfirm={confirmCancel}
/>
