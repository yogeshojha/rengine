<script lang="ts">
	import { goto } from '$app/navigation';
	import { relativeTime } from '$lib/utilities/dates';
	import { getCategoryLabel, type ActivityCluster, type ActivityLevel } from '$lib/types/activity';
	import { activityFeed, getActivityIcon } from '$lib/stores/activity-feed.svelte';
	import { ChevronRight, Loader, ArrowUpRight } from 'lucide-svelte';

	interface Props {
		cluster: ActivityCluster;
		tick?: number;
		isNew?: boolean;
		runningIds?: Set<string>;
	}

	let { cluster, tick = 0, isNew = false, runningIds = new Set() }: Props = $props();

	let expanded = $state(false);
	let multi = $derived(cluster.items.length > 1);
	let primary = $derived(cluster.items[0]);
	let running = $derived(cluster.items.some((i) => runningIds.has(i.id)));
	let timeAgo = $derived.by(() => {
		void tick;
		return relativeTime(cluster.timestamp);
	});

	const nodeTint: Record<ActivityLevel, string> = {
		success: 'bg-muted text-foreground ring-1 ring-border',
		info: 'bg-muted text-muted-foreground ring-1 ring-border',
		warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-500 ring-1 ring-amber-500/30',
		error: 'bg-destructive/10 text-destructive ring-1 ring-destructive/40'
	};
	const RUNNING_TINT = 'bg-chart-1/10 text-chart-1 ring-1 ring-chart-1/30';

	function navigate(targetId: string | null) {
		if (!targetId) return;
		goto(`/targets/${targetId}`);
		activityFeed.setOpen(false);
	}
</script>

{#snippet node(level: ActivityLevel, eventType: string, isRunning: boolean)}
	{@const Icon = getActivityIcon(eventType)}
	<div class="relative z-[1] flex w-5 shrink-0 justify-center">
		<div
			class="mt-px flex h-5 w-5 items-center justify-center rounded-full {isRunning
				? RUNNING_TINT
				: (nodeTint[level] ?? nodeTint.info)}"
		>
			{#if isRunning}
				<Loader class="h-3 w-3 animate-spin" />
			{:else}
				<Icon class="h-3 w-3" />
			{/if}
		</div>
	</div>
{/snippet}

{#snippet meta(isNew: boolean)}
	<div class="mt-0.5 flex shrink-0 items-center gap-1.5">
		<span class="font-mono text-[10px] tabular-nums text-muted-foreground">{timeAgo}</span>
		{#if isNew}
			<span
				class="new-badge inline-flex h-4 items-center rounded px-1 text-[10px] font-semibold uppercase tracking-wide text-chart-1"
			>
				new
			</span>
		{/if}
	</div>
{/snippet}

<div class="group/item relative flex gap-2.5 pb-3 last:pb-1" class:is-new={isNew}>
	{@render node(cluster.level, primary.event_type, running)}

	<div class="min-w-0 flex-1">
		{#if multi}
			<button
				onclick={() => (expanded = !expanded)}
				class="-ml-1 w-[calc(100%+4px)] cursor-pointer rounded-md px-1.5 py-0.5 text-left transition-colors hover:bg-accent/50"
			>
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0 flex-1">
						<span class="line-clamp-1 text-[12px] leading-tight text-foreground"
							>{cluster.label}</span
						>
						<div class="mt-0.5 flex items-center gap-1.5">
							<span class="text-[10px] text-muted-foreground"
								>{getCategoryLabel(primary.event_type)}</span
							>
							<span class="text-muted-foreground/40">·</span>
							<span class="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground">
								{cluster.items.length} events
								<ChevronRight
									class="h-2.5 w-2.5 transition-transform duration-150 {expanded
										? 'rotate-90'
										: ''}"
								/>
							</span>
						</div>
					</div>
					{@render meta(isNew)}
				</div>
			</button>

			{#if expanded}
				<div class="mt-1 space-y-px border-l border-border pl-2.5">
					{#each cluster.items as item (item.id)}
						<button
							type="button"
							onclick={() => navigate(item.target_id)}
							class="group/sub flex w-full items-start gap-1.5 rounded-md px-1 py-[3px] text-left transition-colors hover:bg-accent/40 {item.target_id
								? 'cursor-pointer'
								: 'cursor-default'}"
						>
							<span class="mt-[5px] h-1 w-1 shrink-0 rounded-full {nodeTint[item.level] ?? ''}"
							></span>
							<div class="min-w-0 flex-1">
								<p class="text-[11px] leading-snug text-foreground/80">{item.title}</p>
								{#if item.description}
									<p class="text-[10px] leading-snug text-muted-foreground">{item.description}</p>
								{/if}
							</div>
							{#if item.target_id}
								<ArrowUpRight
									class="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground opacity-40 transition-opacity sm:opacity-0 sm:group-hover/sub:opacity-100"
								/>
							{/if}
						</button>
					{/each}
				</div>
			{/if}
		{:else}
			<svelte:element
				this={primary.target_id ? 'button' : 'div'}
				role={primary.target_id ? 'button' : undefined}
				onclick={() => navigate(primary.target_id)}
				class="group/single -ml-1 flex w-[calc(100%+4px)] items-start justify-between gap-3 rounded-md px-1.5 py-0.5 text-left transition-colors hover:bg-accent/50 {primary.target_id
					? 'cursor-pointer'
					: ''}"
			>
				<div class="min-w-0 flex-1">
					<div class="flex items-center gap-1.5">
						<span class="line-clamp-1 text-[12px] leading-tight text-foreground"
							>{primary.title}</span
						>
						{#if running}
							<span class="shrink-0 text-[10px] font-medium uppercase tracking-wide text-chart-1"
								>running</span
							>
						{/if}
						{#if primary.target_id}
							<ArrowUpRight
								class="h-3 w-3 shrink-0 text-muted-foreground opacity-40 transition-opacity sm:opacity-0 sm:group-hover/single:opacity-100"
							/>
						{/if}
					</div>
					{#if primary.description}
						<p class="mt-0.5 line-clamp-1 text-[10px] text-muted-foreground">
							{primary.description}
						</p>
					{:else}
						<p class="mt-0.5 text-[10px] text-muted-foreground">
							{getCategoryLabel(primary.event_type)}
						</p>
					{/if}
				</div>
				{@render meta(isNew)}
			</svelte:element>
		{/if}
	</div>
</div>

<style>
	.is-new {
		animation:
			slide-in 0.25s ease-out,
			flash 1.4s ease-out;
		border-radius: 6px;
	}
	.new-badge {
		animation: fade-out 5s ease-out forwards;
	}
	@keyframes slide-in {
		from {
			opacity: 0;
			transform: translateY(-3px);
		}
	}
	@keyframes flash {
		0% {
			background-color: hsl(var(--primary) / 0.07);
		}
		100% {
			background-color: transparent;
		}
	}
	@keyframes fade-out {
		0%,
		70% {
			opacity: 1;
		}
		100% {
			opacity: 0;
		}
	}
</style>
