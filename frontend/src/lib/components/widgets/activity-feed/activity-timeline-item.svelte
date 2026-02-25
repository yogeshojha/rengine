<script lang="ts">
	import { relativeTime } from '$lib/utilities/dates';
	import { getCategoryLabel, type ActivityCluster, type ActivityLevel } from '$lib/types/activity';
	import { CircleCheck, TriangleAlert, CircleX, Info, ChevronRight } from 'lucide-svelte';

	interface Props {
		cluster: ActivityCluster;
		tick?: number;
		isNew?: boolean;
	}

	let { cluster, tick = 0, isNew = false }: Props = $props();

	let isExpanded = $state(false);
	let isMulti = $derived(cluster.items.length > 1);
	let timeAgo = $derived.by(() => {
		void tick;
		return relativeTime(cluster.timestamp);
	});

	function toggle() {
		isExpanded = !isExpanded;
	}

	const dotStyles: Record<ActivityLevel, string> = {
		success: 'bg-emerald-500 ring-4 ring-emerald-500/10',
		info: 'bg-transparent border-[2px] border-muted-foreground/25',
		warning: 'bg-amber-500 ring-4 ring-amber-500/10',
		error: 'bg-red-500 ring-4 ring-red-500/10'
	};

	const iconColors: Record<ActivityLevel, string> = {
		success: 'text-emerald-500',
		info: 'text-muted-foreground',
		warning: 'text-amber-500',
		error: 'text-red-500'
	};

	let dot = $derived(dotStyles[cluster.level] ?? dotStyles.info);
</script>

{#snippet levelIcon(level: ActivityLevel, className: string)}
	{#if level === 'success'}
		<CircleCheck class={className} />
	{:else if level === 'warning'}
		<TriangleAlert class={className} />
	{:else if level === 'error'}
		<CircleX class={className} />
	{:else}
		<Info class={className} />
	{/if}
{/snippet}

<div class="timeline-item relative pl-6 pb-5 last:pb-1" class:is-new={isNew}>
	<div
		class="absolute left-0 top-[5px] h-[9px] w-[9px] -translate-x-[4.5px] rounded-full {dot}"
	></div>

	{#if isMulti}
		<button onclick={toggle} class="group w-full text-left cursor-pointer">
			<div class="flex items-start justify-between gap-2">
				<div class="min-w-0 flex-1">
					<div class="flex items-center gap-2">
						<p class="truncate text-xs leading-relaxed text-foreground">{cluster.label}</p>
						{#if isNew}<span class="new-badge text-[9px] font-medium text-muted-foreground/50"
								>new</span
							>{/if}
					</div>
					<div class="mt-0.5 flex items-center gap-1.5">
						<span class="text-[10px] font-medium tracking-wide text-muted-foreground/50">
							{getCategoryLabel(cluster.items[0].event_type)}
						</span>
						<ChevronRight
							class="h-3 w-3 text-muted-foreground/30 transition-transform duration-200
								{isExpanded ? 'rotate-90' : 'group-hover:translate-x-0.5'}"
						/>
					</div>
				</div>
				<span class="mt-0.5 shrink-0 text-[10px] tabular-nums text-muted-foreground/40">
					{timeAgo}
				</span>
			</div>
		</button>

		{#if isExpanded}
			<div class="mt-2 ml-0.5 space-y-1.5 border-l border-border/30 pl-3 animate-expand">
				{#each cluster.items as item (item.id)}
					<div class="flex items-start gap-2 py-0.5">
						{@render levelIcon(
							item.level,
							`h-3 w-3 shrink-0 mt-px ${iconColors[item.level] ?? iconColors.info}`
						)}
						<div class="min-w-0 flex-1">
							<p class="text-[11px] leading-snug text-muted-foreground">{item.title}</p>
							{#if item.description}
								<p class="text-[10px] text-muted-foreground/40 leading-relaxed">
									{item.description}
								</p>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{:else}
		{@const item = cluster.items[0]}
		<div class="flex items-start justify-between gap-2">
			<div class="min-w-0 flex-1">
				<div class="flex items-center gap-2">
					<p class="truncate text-xs leading-relaxed text-foreground">{item.title}</p>
					{#if isNew}<span class="new-badge text-[9px] font-medium text-muted-foreground/50"
							>new</span
						>{/if}
				</div>
				{#if item.description}
					<p class="mt-0.5 text-[10px] text-muted-foreground/40 leading-relaxed">
						{item.description}
					</p>
				{/if}
			</div>
			<span class="mt-0.5 shrink-0 text-[10px] tabular-nums text-muted-foreground/40">
				{timeAgo}
			</span>
		</div>
	{/if}
</div>

<style>
	.is-new {
		box-shadow: inset 2px 0 0 hsl(var(--border));
		animation:
			slide-in 0.4s cubic-bezier(0.22, 1, 0.36, 1),
			fade-accent 5s ease-out forwards;
	}

	.new-badge {
		animation: fade-out 5s ease-out forwards;
	}

	@keyframes slide-in {
		from {
			opacity: 0;
			transform: translateY(-6px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes fade-accent {
		0%,
		70% {
			box-shadow: inset 2px 0 0 hsl(var(--border));
		}
		100% {
			box-shadow: inset 2px 0 0 transparent;
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

	@keyframes expand {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.animate-expand {
		animation: expand 0.2s ease-out;
	}
</style>
