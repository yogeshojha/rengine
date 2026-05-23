<script lang="ts">
	import { untrack, onMount } from 'svelte';
	import { activityApi } from '$lib/api/activity';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { activityScope } from '$lib/stores/activity-scope.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import {
		clusterEvents,
		groupByDay,
		type ActivityLog,
		type ActivityLevel
	} from '$lib/types/activity';
	import { relativeTime } from '$lib/utilities/dates';
	import ActivityTimeline from './activity-timeline.svelte';
	import { ChevronUp, ChevronDown, X, GripHorizontal } from 'lucide-svelte';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';

	let projectId = $derived(projectsStore.activeProject?.id);
	let targetId = $derived(activityScope.targetId);
	let scanId = $derived(activityScope.scanId);
	let hasTarget = $derived(!!targetId);

	let open = $state(false);
	let filter = $state('all');
	let scope = $state<'current' | 'project'>('current');
	let tick = $state(0);
	let newCount = $state(0);

	let items = $state<ActivityLog[]>([]);
	let pg = $state(1);
	let totalPages = $state(1);
	let loading = $state(false);
	let initialLoad = $state(true);
	let freshIds = $state<Set<string>>(new Set());

	let sentinelEl = $state<HTMLDivElement | null>(null);
	let panelEl = $state<HTMLDivElement | null>(null);

	let scoped = $derived.by(() => {
		if (scope === 'project' || !targetId) return items;
		return items.filter((a) => a.target_id === targetId);
	});

	let filtered = $derived.by(() => {
		if (filter === 'all') return scoped;
		return scoped.filter((a) => categorize(a.event_type) === filter);
	});

	let clusters = $derived(clusterEvents(filtered));
	let days = $derived(groupByDay(clusters));
	let hasMore = $derived(pg < totalPages);

	let latest = $derived.by(() => {
		const pool = hasTarget ? items.filter((a) => a.target_id === targetId) : items;
		return pool[0] ?? null;
	});

	let counts = $derived.by(() => {
		const c: Record<string, number> = { all: scoped.length };
		for (const a of scoped) {
			const k = categorize(a.event_type);
			c[k] = (c[k] ?? 0) + 1;
		}
		return c;
	});

	let scopeLabel = $derived(scanId ? 'Scan' : hasTarget ? 'Target' : 'Project');

	const PANEL_MIN = 200;
	const PANEL_MAX_RATIO = 0.6;
	const PANEL_DEFAULT_RATIO = 0.35;

	let panelHeight = $state(0);

	onMount(() => {
		panelHeight = Math.round(window.innerHeight * PANEL_DEFAULT_RATIO);
	});
	let isDragging = $state(false);
	let dragStartY = $state(0);
	let dragStartH = $state(0);

	$effect(() => {
		function onResize() {
			const max = window.innerHeight * PANEL_MAX_RATIO;
			if (panelHeight > max) panelHeight = max;
			if (panelHeight < PANEL_MIN) panelHeight = PANEL_MIN;
		}
		window.addEventListener('resize', onResize);
		return () => window.removeEventListener('resize', onResize);
	});

	function onDragStart(e: PointerEvent) {
		e.preventDefault();
		isDragging = true;
		dragStartY = e.clientY;
		dragStartH = panelHeight;
		(e.target as HTMLElement).setPointerCapture(e.pointerId);
	}

	function onDragMove(e: PointerEvent) {
		if (!isDragging) return;
		const delta = dragStartY - e.clientY;
		const max = window.innerHeight * PANEL_MAX_RATIO;
		panelHeight = Math.max(PANEL_MIN, Math.min(max, dragStartH + delta));
	}

	function onDragEnd() {
		isDragging = false;
	}

	function onWindowPointerDown(e: PointerEvent) {
		if (!open || isDragging) return;
		const target = e.target as HTMLElement;
		if (panelEl && panelEl.contains(target)) return;
		if (target.closest('.activity-bar-btn')) return;
		open = false;
	}

	const FILTERS = ['all', 'scan', 'enrichment', 'alert', 'system'] as const;
	const FILTER_LABELS: Record<string, string> = {
		all: 'All',
		scan: 'Scans',
		enrichment: 'Enrichment',
		alert: 'Alerts',
		system: 'System'
	};

	const dotColor: Record<ActivityLevel, string> = {
		success: 'bg-emerald-500',
		info: 'bg-muted-foreground/50',
		warning: 'bg-amber-500',
		error: 'bg-red-500'
	};

	function categorize(t: string): string {
		const s = t.toLowerCase();
		if (/scan|recon|nuclei|task/.test(s)) return 'scan';
		if (/enrich|whois|dns|bgp|geoip|ssl/.test(s)) return 'enrichment';
		if (/alert|vuln|critical/.test(s)) return 'alert';
		return 'system';
	}

	async function load(p: number) {
		if (loading || !projectId) return;
		loading = true;
		try {
			const res = await activityApi.list({ project_id: projectId }, p, 50);
			if (p === 1) {
				items = res.items;
			} else {
				const seen = new Set(items.map((a) => a.id));
				items = [...items, ...res.items.filter((i) => !seen.has(i.id))];
			}
			totalPages = res.pages;
			pg = p;
		} catch (e) {
			console.error('[ActivityDrawer]', e);
		} finally {
			loading = false;
			initialLoad = false;
		}
	}

	$effect(() => {
		if (!sentinelEl) return;
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries[0]?.isIntersecting && hasMore && !loading) {
					load(pg + 1);
				}
			},
			{ threshold: 0 }
		);
		observer.observe(sentinelEl);
		return () => observer.disconnect();
	});

	$effect(() => {
		const pid = projectId;
		untrack(() => {
			if (pid) load(1);
		});
	});

	$effect(() => {
		if (!projectId) return;
		return sseStore.on<ActivityLog>(SSEChannel.project(projectId), SSEEventType.ACTIVITY, (d) => {
			if (items.some((a) => a.id === d.id)) return;
			freshIds = new Set([...freshIds, d.id]);
			items = [d, ...items];
			if (!open) newCount++;
			setTimeout(() => {
				freshIds = new Set([...freshIds].filter((id) => id !== d.id));
			}, 5000);
		});
	});

	$effect(() => {
		if (open) newCount = 0;
	});

	$effect(() => {
		if (!open) return;
		const iv = setInterval(() => tick++, 30_000);
		return () => clearInterval(iv);
	});

	$effect(() => {
		void targetId;
		scope = 'current';
		filter = 'all';
	});
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape' && open) open = false;
	}}
	onpointerdown={onWindowPointerDown}
/>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	bind:this={panelEl}
	class="activity-panel absolute inset-x-0 bottom-9 z-10 overflow-hidden rounded-t-lg"
	class:no-transition={isDragging}
	style="height:{open ? panelHeight : 0}px"
>
	<div
		class="flex flex-col border-t border-x border-border bg-background rounded-t-lg"
		style="height:{panelHeight}px"
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="drag-handle flex shrink-0 items-center justify-center h-3 cursor-ns-resize group/drag
				hover:bg-accent/40 transition-colors"
			onpointerdown={onDragStart}
			onpointermove={onDragMove}
			onpointerup={onDragEnd}
			onpointercancel={onDragEnd}
		>
			<GripHorizontal
				class="h-3 w-3 text-muted-foreground/40 group-hover/drag:text-muted-foreground transition-colors"
			/>
		</div>

		<div class="flex shrink-0 items-center justify-between px-3 pt-0.5 pb-2">
			<div class="flex items-center gap-3">
				<span
					class="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.05em] text-muted-foreground"
				>
					{#if sseStore.isConnected}
						<span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
					{/if}
					Recent Activities
				</span>

				{#if hasTarget}
					<Tabs.Root value={scope} onValueChange={(v) => (scope = v as 'current' | 'project')}>
						<Tabs.List class="h-7">
							<Tabs.Trigger value="current" class="text-[10px] px-2.5 h-5">Current</Tabs.Trigger>
							<Tabs.Trigger value="project" class="text-[10px] px-2.5 h-5">Project</Tabs.Trigger>
						</Tabs.List>
					</Tabs.Root>
				{/if}
			</div>

			<button
				type="button"
				onclick={() => (open = false)}
				class="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground
					transition-colors hover:bg-accent hover:text-foreground"
			>
				<X class="h-3.5 w-3.5" />
			</button>
		</div>

		<div class="flex shrink-0 items-center gap-1 px-3 pb-2">
			{#each FILTERS as f}
				{@const n = counts[f] ?? 0}
				{#if f === 'all' || n > 0}
					<button
						type="button"
						class="rounded-full px-2.5 py-[3px] text-[10px] font-medium transition-colors
							{filter === f
							? 'bg-accent text-foreground ring-1 ring-border'
							: 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'}"
						onclick={() => (filter = f)}
					>
						{FILTER_LABELS[f]}
						<span class="ml-0.5 font-mono text-[9px] opacity-60">{n}</span>
					</button>
				{/if}
			{/each}
		</div>

		<Separator />

		<div class="relative flex-1 min-h-0">
			<ScrollArea class="h-full">
				<div class="px-3 pt-2 pb-4">
					<ActivityTimeline
						dayGroups={days}
						newEventIds={freshIds}
						{tick}
						isLoading={initialLoad}
						isEmpty={!initialLoad && filtered.length === 0}
					/>

					{#if loading && !initialLoad}
						<div class="flex justify-center py-3">
							<Spinner class="h-3.5 w-3.5 text-muted-foreground" />
						</div>
					{/if}

					{#if hasMore && !initialLoad}
						<div bind:this={sentinelEl} class="h-1"></div>
					{/if}
				</div>
			</ScrollArea>

			<div
				class="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-background to-transparent"
			></div>
		</div>
	</div>
</div>

<button
	type="button"
	onclick={() => (open = !open)}
	class="activity-bar-btn flex h-9 w-full shrink-0 cursor-pointer items-center border-t border-border bg-background
		transition-colors hover:bg-accent/30"
>
	<div class="flex items-center gap-2 self-stretch shrink-0 border-r border-border px-3">
		<span
			class="h-1.5 w-1.5 rounded-full {sseStore.isConnected
				? 'bg-emerald-500'
				: sseStore.isReconnecting
					? 'bg-amber-500'
					: 'bg-muted-foreground/30'}"
		></span>
		<span class="text-[10px] font-medium tracking-wide text-muted-foreground">{scopeLabel}</span>
	</div>

	<div class="mx-2.5 flex-1 min-w-0 h-[18px] overflow-hidden">
		{#if latest}
			<div class="flex h-[18px] items-center gap-1.5 whitespace-nowrap">
				<span class="h-1 w-1 shrink-0 rounded-full {dotColor[latest.level] ?? dotColor.info}"
				></span>
				<span class="truncate text-[11px] text-foreground/70">{latest.title}</span>
				<span class="shrink-0 font-mono text-[9px] tabular-nums text-muted-foreground">
					{relativeTime(latest.timestamp)}
				</span>
			</div>
		{:else if initialLoad}
			<div class="flex h-[18px] items-center gap-1.5">
				<span class="h-1 w-1 rounded-full bg-muted animate-pulse"></span>
				<span class="h-2.5 w-32 rounded bg-muted/60 animate-pulse"></span>
			</div>
		{:else}
			<span class="flex h-[18px] items-center text-[11px] text-muted-foreground">
				No recent activity
			</span>
		{/if}
	</div>

	<div class="flex shrink-0 items-center gap-2.5 pr-3">
		{#if newCount > 0}
			<Badge
				variant="secondary"
				class="h-5 gap-1 rounded-md px-2 text-[10px] font-semibold text-emerald-500 bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/10"
			>
				{newCount} new
			</Badge>
		{/if}

		{#if open}
			<ChevronDown class="h-3.5 w-3.5 text-muted-foreground" />
		{:else}
			<ChevronUp class="h-3.5 w-3.5 text-muted-foreground" />
		{/if}
	</div>
</button>

<style>
	.activity-panel {
		transition: height 0.25s cubic-bezier(0.22, 1, 0.36, 1);
		box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.12);
	}

	.activity-panel.no-transition {
		transition: none;
	}

	.drag-handle {
		touch-action: none;
	}
</style>
