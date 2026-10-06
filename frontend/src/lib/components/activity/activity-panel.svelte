<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { activityFeed } from '$lib/stores/activity-feed.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import { ACTIVITY_TICK_MS, NOW_TICK_MS } from '$lib/constants';
	import { ACTIVITY_LIVE_CARDS } from '$lib/config/activity';
	import { ROUTES } from '$lib/config/routes';
	import type { ActivityLog } from '$lib/types/activity';
	import type { ScanRead } from '$lib/types/scan';
	import ActivityRow from './activity-row.svelte';
	import LiveScanCard from '$lib/components/scans/live-scan-card.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Button } from '$lib/components/ui/button';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import Pin from '@lucide/svelte/icons/pin';
	import PinOff from '@lucide/svelte/icons/pin-off';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';

	const PANEL_W = 360;
	const sidebar = useSidebar();

	let projectId = $derived(projectsStore.activeProject?.id);
	let panelEl = $state<HTMLElement | null>(null);
	let sentinelEl = $state<HTMLDivElement | null>(null);

	let docked = $derived(activityFeed.pinned && !sidebar.isMobile);
	let visibleScans = $derived(liveScans.scans.slice(0, ACTIVITY_LIVE_CARDS));
	let overflow = $derived(liveScans.count - ACTIVITY_LIVE_CARDS);

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
	function onNavigate() {
		if (!docked) activityFeed.setOpen(false);
	}

	let now = $state(Date.now());
	$effect(() => {
		if (!liveScans.hasLive || !activityFeed.open) return;
		const t = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		return () => clearInterval(t);
	});

	$effect(() => {
		if (liveScans.hasLive) untrack(() => engineCatalogStore.fetch());
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

	function onWindowPointerDown(e: PointerEvent) {
		if (!activityFeed.open || docked) return;
		const t = e.target as HTMLElement;
		if (panelEl?.contains(t)) return;
		if (t.closest('[data-activity-glance]')) return;
		if (t.closest('[data-slot=alert-dialog-content]')) return;
		if (t.closest('[data-slot=dialog-content]')) return;
		activityFeed.setOpen(false);
	}

	async function confirmCancel() {
		const scan = cancelTarget;
		if (!scan) return;
		cancelling = true;
		const ok = await liveScans.cancel(scan);
		cancelling = false;
		if (ok) {
			cancelTarget = null;
			toast.success('Scan cancelled');
		} else toast.error('Scan not cancelled');
	}
</script>

<svelte:window
	onkeydown={(e) => {
		if (e.key === 'Escape' && !e.defaultPrevented && activityFeed.open && !docked)
			activityFeed.setOpen(false);
	}}
	onpointerdown={onWindowPointerDown}
/>

<aside
	bind:this={panelEl}
	aria-label="Activity"
	aria-hidden={!activityFeed.open}
	inert={!activityFeed.open}
	class="flex flex-col border-l bg-sidebar {docked
		? 'relative z-10 shrink-0'
		: `absolute inset-y-0 right-0 z-30 shadow-2xl transition-transform duration-300 ease-out ${activityFeed.open ? 'translate-x-0' : 'translate-x-full'}`}"
	style="width: min({PANEL_W}px, 100vw)"
>
	<header class="flex h-12 shrink-0 items-center justify-between gap-2 border-b pr-2 pl-4">
		<div class="flex min-w-0 items-center gap-2">
			<h2 class="text-sm font-semibold">Activity</h2>
			{#if sseStore.isReconnecting}
				<Badge variant="warning" class="h-5 px-1.5 text-2xs">Reconnecting</Badge>
			{/if}
		</div>
		<div class="flex shrink-0 items-center">
			{#if !sidebar.isMobile}
				<Hint text={activityFeed.pinned ? 'Unpin' : 'Pin'} side="bottom">
					{#snippet child(props)}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							onclick={() => activityFeed.setPinned(!activityFeed.pinned)}
							aria-label={activityFeed.pinned ? 'Unpin panel' : 'Pin panel'}
							aria-pressed={activityFeed.pinned}
							class="size-7 {activityFeed.pinned
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
				</Hint>
			{/if}
			<Button
				variant="ghost"
				size="icon"
				onclick={() => activityFeed.setOpen(false)}
				aria-label="Close"
				class="size-7 text-muted-foreground hover:text-foreground"
			>
				<X class="size-3.5" />
			</Button>
		</div>
	</header>

	<ScrollArea class="min-h-0 flex-1">
		<div class="flex flex-col gap-5 p-3">
			{#if liveScans.hasLive}
				<section class="flex flex-col gap-2" aria-label="Running">
					<div class="px-1">
						<SectionHead title="Running" count={liveScans.count} />
					</div>
					{#each visibleScans as scan (scan.id)}
						<LiveScanCard
							{scan}
							run={liveScans.runFor(scan.id)}
							catalog={engineCatalogStore.stages}
							previousDuration={liveScans.previousDuration(scan.id)}
							{now}
							{onNavigate}
							onCancel={(s) => (cancelTarget = s)}
						/>
					{/each}
					{#if overflow > 0}
						<a
							href={ROUTES.scans}
							onclick={onNavigate}
							class="inline-flex items-center gap-1 px-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
						>
							{overflow} more running
							<ArrowRight class="size-3" />
						</a>
					{/if}
				</section>
			{/if}

			{#if activityFeed.initialLoad}
				<div class="flex flex-col gap-2">
					<div class="px-1"><Skeleton class="h-3 w-16" /></div>
					<div class="flex flex-col divide-y rounded-lg border bg-card">
						{#each { length: 4 } as _, i (i)}
							<div class="flex gap-3 px-3 py-2.5">
								<Skeleton class="size-7 shrink-0 rounded-md" />
								<div class="flex flex-1 flex-col gap-1.5 py-0.5">
									<Skeleton class="h-3 rounded" style="width:{70 - i * 10}%" />
									<Skeleton class="h-2.5 w-24 rounded" />
								</div>
							</div>
						{/each}
					</div>
				</div>
			{:else if activityFeed.loadError && activityFeed.isEmpty}
				<div class="flex flex-col items-center gap-3 py-12 text-center">
					<TriangleAlert class="size-4 text-muted-foreground" />
					<p class="text-sm text-muted-foreground">Activity not loaded</p>
					<Button
						size="sm"
						variant="outline"
						onclick={() => {
							if (projectId) activityFeed.load(projectId, 1);
						}}
					>
						Retry
					</Button>
				</div>
			{:else if activityFeed.isEmpty && !liveScans.hasLive}
				<p class="py-12 text-center text-sm text-muted-foreground">No activity</p>
			{:else}
				{#each activityFeed.days as day (day.date)}
					<section class="flex flex-col gap-2" aria-label={day.label}>
						<div class="px-1">
							<SectionHead title={day.label} />
						</div>
						<ol class="flex flex-col divide-y overflow-hidden rounded-lg border bg-card shadow-xs">
							{#each day.rows as row (row.id)}
								<li>
									<ActivityRow {row} tick={activityFeed.tick} {onNavigate} onRescan={rescan} />
								</li>
							{/each}
						</ol>
					</section>
				{/each}
			{/if}

			{#if activityFeed.loading && !activityFeed.initialLoad}
				<div class="flex justify-center py-2">
					<Spinner class="size-3.5 text-muted-foreground" />
				</div>
			{/if}
			{#if activityFeed.hasMore && !activityFeed.initialLoad}
				<div bind:this={sentinelEl} class="h-1"></div>
			{/if}
		</div>
	</ScrollArea>

	<footer class="flex shrink-0 justify-end border-t px-4 py-2.5">
		<a
			href={ROUTES.scans}
			onclick={onNavigate}
			class="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
		>
			All scans
			<ArrowRight class="size-3" />
		</a>
	</footer>
</aside>

<LaunchDialog bind:open={rescanOpen} targetId={rescanTargetId} onClose={onRescanClose} />

<ConfirmDialog
	open={!!cancelTarget}
	title="Cancel scan"
	description="The scan stops and is marked cancelled."
	confirmLabel="Cancel scan"
	cancelLabel="Keep running"
	destructive
	loading={cancelling}
	loadingLabel="Cancelling"
	onOpenChange={(o) => {
		if (!o) cancelTarget = null;
	}}
	onConfirm={confirmCancel}
/>
