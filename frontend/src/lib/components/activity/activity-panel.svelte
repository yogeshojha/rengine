<script lang="ts">
	import { untrack } from 'svelte';
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
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import { ACTIVITY_TICK_MS, NOW_TICK_MS } from '$lib/constants';
	import type { ActivityLog } from '$lib/types/activity';
	import ActivityTimeline from './activity-timeline.svelte';
	import LiveScanRow from '$lib/components/scans/live-scan-row.svelte';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Collapsible from '$lib/components/ui/collapsible/index.js';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Search from '@lucide/svelte/icons/search';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import X from '@lucide/svelte/icons/x';

	const PANEL_W = 360;

	let projectId = $derived(projectsStore.activeProject?.id);
	let panelEl = $state<HTMLElement | null>(null);
	let sentinelEl = $state<HTMLDivElement | null>(null);
	let scrollEl = $state<HTMLDivElement | null>(null);
	let scrollTop = $state(0);

	let showJump = $derived(scrollTop > 80 && activityFeed.freshIds.size > 0);
	let runningOpen = $state(true);

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
		if (!activityFeed.open) return;
		const t = e.target as HTMLElement;
		if (panelEl?.contains(t)) return;
		if (t.closest('[data-activity-glance]')) return;
		activityFeed.setOpen(false);
	}

	function jumpToLive() {
		scrollEl?.scrollTo({ top: 0, behavior: 'smooth' });
	}
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape' && activityFeed.open) activityFeed.setOpen(false);
	}}
	onpointerdown={onWindowPointerDown}
/>

<aside
	bind:this={panelEl}
	class="absolute inset-y-0 right-0 z-30 flex flex-col border-l border-border bg-background shadow-2xl transition-transform duration-300 ease-out {activityFeed.open
		? 'translate-x-0'
		: 'translate-x-full'}"
	style="width: {PANEL_W}px"
>
	<div class="flex shrink-0 items-center justify-between gap-2 px-3 py-2.5">
		<div class="flex min-w-0 items-center gap-2">
			<span class="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
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

		<Button
			variant="ghost"
			size="icon-sm"
			onclick={() => activityFeed.setOpen(false)}
			title="Close"
			class="h-6 w-6 shrink-0 text-muted-foreground hover:text-foreground"
		>
			<X class="h-3.5 w-3.5" />
		</Button>
	</div>

	<div class="px-3 pb-2">
		<div class="relative">
			<Search class="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
			<Input
				value={activityFeed.search}
				oninput={(e) => activityFeed.setSearch(e.currentTarget.value)}
				placeholder="Search activity…"
				class="h-7 border-border bg-muted/30 pl-7 pr-7 text-[11px] transition-colors focus:border-primary/40 focus:bg-background"
			/>
			{#if activityFeed.search}
				<button
					type="button"
					onclick={() => activityFeed.setSearch('')}
					class="absolute right-1.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
				>
					<X class="h-3 w-3" />
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
					class="rounded-full px-2.5 py-[3px] text-[10px] font-medium transition-colors {activityFeed.filter ===
					f
						? 'bg-accent text-foreground ring-1 ring-border'
						: 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'}"
					onclick={() => activityFeed.setFilter(f as ActivityFilter)}
				>
					{FILTER_LABELS[f]}
					<span class="ml-0.5 font-mono text-[9px] opacity-60">{n}</span>
				</button>
			{/if}
		{/each}

		<div class="ml-auto">
			<button
				type="button"
				title="Errors only"
				onclick={() => activityFeed.toggleErrorsOnly()}
				class="inline-flex items-center gap-1 rounded-full px-2 py-[3px] text-[10px] font-medium transition-colors {activityFeed.errorsOnly
					? 'bg-destructive/10 text-destructive ring-1 ring-destructive/40'
					: 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'}"
			>
				<ShieldAlert class="h-3 w-3" />
				Errors
			</button>
		</div>
	</div>

	{#if liveScans.hasLive}
		<Collapsible.Root bind:open={runningOpen} class="mx-3 mb-2 shrink-0">
			<div class="overflow-hidden rounded-md border border-info/20 bg-info/5">
				<Collapsible.Trigger
					class="flex w-full items-center justify-between px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-info transition-colors hover:bg-info/10"
				>
					<span class="flex items-center gap-1.5">
						<Spinner class="size-3" />
						Running now
						<span class="font-mono tabular-nums opacity-70">{liveScans.count}</span>
					</span>
					<ChevronDown
						class="size-3 transition-transform duration-150 {runningOpen ? '' : '-rotate-90'}"
					/>
				</Collapsible.Trigger>
				<Collapsible.Content>
					<div class="space-y-px px-1 pb-1">
						{#each liveScans.scans as scan (scan.id)}
							<LiveScanRow
								{scan}
								stage={liveScans.stageFor(scan.id)}
								{now}
								onNavigate={() => activityFeed.setOpen(false)}
							/>
						{/each}
					</div>
				</Collapsible.Content>
			</div>
		</Collapsible.Root>
	{/if}

	<Separator />

	<div class="relative min-h-0 flex-1">
		{#if showJump}
			<button
				type="button"
				onclick={jumpToLive}
				class="absolute left-1/2 top-2 z-20 inline-flex -translate-x-1/2 items-center gap-1 rounded-full border border-primary/20 bg-primary px-2.5 py-1 text-[10px] font-semibold text-primary-foreground shadow-lg transition-transform hover:scale-105"
			>
				<ArrowUp class="h-3 w-3" />
				{activityFeed.freshIds.size} new
			</button>
		{/if}

		<ScrollArea class="h-full" bind:viewportRef={scrollEl}>
			<div class="px-3 pb-4 pt-2">
				<ActivityTimeline
					dayGroups={activityFeed.days}
					newEventIds={activityFeed.freshIds}
					runningIds={activityFeed.runningIds}
					tick={activityFeed.tick}
					isLoading={activityFeed.initialLoad}
					isEmpty={!activityFeed.initialLoad && activityFeed.filtered.length === 0}
				/>

				{#if activityFeed.loading && !activityFeed.initialLoad}
					<div class="flex justify-center py-3">
						<Spinner class="h-3.5 w-3.5 text-muted-foreground" />
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
