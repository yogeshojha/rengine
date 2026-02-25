<script lang="ts">
	import { untrack } from 'svelte';
	import { activityApi } from '$lib/api/activity';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import { clusterEvents, groupByDay, type ActivityLog } from '$lib/types/activity';
	import { Activity } from 'lucide-svelte';
	import ActivityTimeline from './activity-timeline.svelte';

	interface Props {
		projectId?: string;
		targetId?: string;
		title?: string;
		pageSize?: number;
	}

	let { projectId, targetId, title = 'Activity', pageSize = 30 }: Props = $props();

	let activities = $state<ActivityLog[]>([]);
	let currentPage = $state(1);
	let totalPages = $state(1);
	let isLoading = $state(false);
	let isInitialLoad = $state(true);
	let newEventIds = $state<Set<string>>(new Set());

	let scrollEl: HTMLDivElement | undefined = $state();
	let sentinelEl: HTMLDivElement | undefined = $state();
	let tick = $state(0);

	$effect(() => {
		const interval = setInterval(() => {
			tick++;
		}, 30_000);
		return () => clearInterval(interval);
	});

	let clusters = $derived(clusterEvents(activities));
	let dayGroups = $derived(groupByDay(clusters));
	let hasMore = $derived(currentPage < totalPages);

	async function loadPage(page: number) {
		if (isLoading) return;
		isLoading = true;

		try {
			const filters: Record<string, string> = {};
			if (projectId) filters.project_id = projectId;
			if (targetId) filters.target_id = targetId;

			const res = await activityApi.list(filters, page, pageSize);

			if (page === 1) {
				activities = res.items;
			} else {
				const existingIds = new Set(activities.map((a) => a.id));
				const newItems = res.items.filter((i) => !existingIds.has(i.id));
				activities = [...activities, ...newItems];
			}

			totalPages = res.pages;
			currentPage = page;
		} catch (err) {
			console.error('[ActivityFeed] Load failed:', err);
		} finally {
			isLoading = false;
			isInitialLoad = false;
		}
	}

	$effect(() => {
		if (!projectId) return;
		const tid = targetId;

		const unsub = sseStore.on<ActivityLog>(
			SSEChannel.project(projectId),
			SSEEventType.ACTIVITY,
			(data) => {
				if (tid && data.target_id !== tid) return;
				if (activities.some((a) => a.id === data.id)) return;

				newEventIds = new Set([...newEventIds, data.id]);
				activities = [data, ...activities];

				setTimeout(() => {
					newEventIds = new Set([...newEventIds].filter((id) => id !== data.id));
				}, 5500);
			}
		);

		return unsub;
	});

	$effect(() => {
		if (!sentinelEl || !scrollEl) return;

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries[0]?.isIntersecting && hasMore && !isLoading) {
					loadPage(currentPage + 1);
				}
			},
			{ root: scrollEl, threshold: 0.1 }
		);

		observer.observe(sentinelEl);
		return () => observer.disconnect();
	});

	$effect(() => {
		const pid = projectId;
		const tid = targetId;

		untrack(() => {
			if (pid || tid) {
				loadPage(1);
			}
		});
	});
</script>

<div class="flex h-full flex-col rounded-lg border border-border bg-card">
	<div class="flex items-center justify-between border-b border-border px-4 py-3">
		<div class="flex items-center gap-2">
			<Activity class="h-3.5 w-3.5 text-muted-foreground/60" />
			<h3 class="text-[13px] font-medium text-foreground">{title}</h3>
		</div>
		{#if sseStore.isConnected && projectId}
			<div class="flex items-center gap-1.5">
				<span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
				<span class="text-[9px] font-medium uppercase tracking-widest text-muted-foreground/40">
					Live
				</span>
			</div>
		{/if}
	</div>

	<div class="relative min-h-0 flex-1">
		<div bind:this={scrollEl} class="h-full overflow-y-auto px-4 pt-3 pb-8 scrollbar-thin">
			<ActivityTimeline
				{dayGroups}
				{newEventIds}
				{tick}
				isLoading={isInitialLoad}
				isEmpty={!isInitialLoad && activities.length === 0}
				{hasMore}
			/>

			{#if hasMore}
				<div bind:this={sentinelEl} class="h-px"></div>
			{/if}
		</div>

		<div
			class="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-card to-transparent"
		></div>
	</div>
</div>

<style>
	.scrollbar-thin {
		scrollbar-width: none;
		-ms-overflow-style: none;
	}
	.scrollbar-thin::-webkit-scrollbar {
		display: none;
	}
</style>
