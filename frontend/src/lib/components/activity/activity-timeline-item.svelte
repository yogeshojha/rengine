<script lang="ts">
	import { relativeTime } from '$lib/utilities/dates';
	import { getCategoryLabel, type ActivityCluster, type ActivityLevel } from '$lib/types/activity';
	import { CircleCheck, TriangleAlert, CircleX, Info, ChevronRight } from 'lucide-svelte';
	import { Badge } from '$lib/components/ui/badge/index.js';

	interface Props {
		cluster: ActivityCluster;
		tick?: number;
		isNew?: boolean;
	}

	let { cluster, tick = 0, isNew = false }: Props = $props();

	let expanded = $state(false);
	let multi = $derived(cluster.items.length > 1);
	let primary = $derived(cluster.items[0]);
	let timeAgo = $derived.by(() => {
		void tick;
		return relativeTime(cluster.timestamp);
	});

	const dots: Record<ActivityLevel, string> = {
		success: 'bg-emerald-500 ring-[3px] ring-emerald-500/10',
		info: 'ring-[1.5px] ring-muted-foreground/30 bg-transparent',
		warning: 'bg-amber-500 ring-[3px] ring-amber-500/10',
		error: 'bg-red-500 ring-[3px] ring-red-500/10'
	};

	const iconColor: Record<ActivityLevel, string> = {
		success: 'text-emerald-500',
		info: 'text-muted-foreground',
		warning: 'text-amber-500',
		error: 'text-red-500'
	};
</script>

{#snippet statusIcon(level: ActivityLevel, cls: string)}
	{#if level === 'success'}<CircleCheck class={cls} />
	{:else if level === 'warning'}<TriangleAlert class={cls} />
	{:else if level === 'error'}<CircleX class={cls} />
	{:else}<Info class={cls} />
	{/if}
{/snippet}

{#snippet timeAndBadge(isNew: boolean)}
	<div class="mt-0.5 flex shrink-0 items-center gap-1.5">
		<span class="text-[10px] tabular-nums font-mono text-muted-foreground">{timeAgo}</span>
		{#if isNew}
			<Badge
				variant="secondary"
				class="new-badge h-4 rounded px-1 text-[8px] font-semibold uppercase tracking-wide
					text-cyan-500 bg-cyan-500/10 border-cyan-500/20 hover:bg-cyan-500/10"
			>
				new
			</Badge>
		{/if}
	</div>
{/snippet}

<div class="group/item relative pb-3 pl-5 last:pb-1" class:is-new={isNew}>
	<!-- timeline dot -->
	<span
		class="absolute left-0 top-[6px] z-[1] h-[7px] w-[7px] -translate-x-1/2 rounded-full
			{dots[cluster.level] ?? dots.info}"
	></span>

	{#if multi}
		<button
			onclick={() => (expanded = !expanded)}
			class="group/cluster -ml-1 w-[calc(100%+4px)] cursor-pointer rounded-md px-1.5 py-1
				text-left transition-colors hover:bg-accent/50"
		>
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0 flex-1">
					<span class="text-[12px] leading-tight text-foreground line-clamp-1">
						{cluster.label}
					</span>
					<div class="mt-0.5 flex items-center gap-1.5">
						<span class="text-[10px] text-muted-foreground">
							{getCategoryLabel(primary.event_type)}
						</span>
						<span class="text-muted-foreground/40">·</span>
						<span
							class="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground
								transition-colors group-hover/cluster:text-foreground"
						>
							{cluster.items.length} events
							<ChevronRight
								class="h-2.5 w-2.5 transition-transform duration-150
									{expanded ? 'rotate-90' : ''}"
							/>
						</span>
					</div>
				</div>
				{@render timeAndBadge(isNew)}
			</div>
		</button>

		{#if expanded}
			<div class="mt-1 ml-0.5 border-l border-border pl-2.5">
				{#each cluster.items as item (item.id)}
					<div
						class="flex items-start gap-1.5 rounded-md px-1 py-[3px] transition-colors hover:bg-accent/30"
					>
						{@render statusIcon(item.level, `h-3 w-3 shrink-0 mt-[1px] ${iconColor[item.level]}`)}
						<div class="min-w-0 flex-1">
							<p class="text-[11px] leading-snug text-foreground/80">{item.title}</p>
							{#if item.description}
								<p class="text-[10px] leading-snug text-muted-foreground">
									{item.description}
								</p>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{:else}
		<div
			class="group/single -ml-1 flex w-[calc(100%+4px)] items-start justify-between gap-3
				rounded-md px-1.5 py-1 transition-colors hover:bg-accent/50"
		>
			<div class="min-w-0 flex-1">
				<span class="text-[12px] leading-tight text-foreground line-clamp-1">
					{primary.title}
				</span>
				{#if primary.description}
					<p class="mt-0.5 text-[10px] text-muted-foreground line-clamp-1">
						{primary.description}
					</p>
				{:else}
					<p class="mt-0.5 text-[10px] text-muted-foreground">
						{getCategoryLabel(primary.event_type)}
					</p>
				{/if}
			</div>
			{@render timeAndBadge(isNew)}
		</div>
	{/if}
</div>

<style>
	.is-new {
		animation: slide-in 0.25s ease-out;
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
