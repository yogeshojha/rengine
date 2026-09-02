<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Copy from '@lucide/svelte/icons/copy';
	import Play from '@lucide/svelte/icons/play';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import type { Intensity, ScanEngine, StageCatalogEntry } from '$lib/types/scan-engine';
	import { INTENSITY_LABELS, phaseLabel } from '$lib/types/scan-engine';
	import { summarize, FOOTPRINT_LABEL, FOOTPRINT_HELP } from '$lib/utilities/engine-summary';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { formatDistanceToNow } from '$lib/utilities/dates';

	interface Props {
		engine: ScanEngine;
		stages: StageCatalogEntry[];
		onEdit?: () => void;
		onRun?: () => void;
		onDuplicate?: () => void;
		onDelete?: () => void;
		isSelected?: boolean;
		onSelect?: () => void;
	}

	let {
		engine,
		stages,
		onEdit,
		onRun,
		onDuplicate,
		onDelete,
		isSelected = false,
		onSelect
	}: Props = $props();

	const summary = $derived(summarize(engine.stages ?? {}, stages, engine.intensity));

	const intensityClass: Record<Intensity, string> = {
		passive: 'text-muted-foreground border-border/60',
		normal: 'text-foreground border-border',
		aggressive: 'text-warning border-warning/30'
	};
	const badgeClass = $derived(intensityClass[engine.intensity] ?? intensityClass.normal);

	function isOn(stage: StageCatalogEntry): boolean {
		return Boolean(engine.stages?.[stage.name]?.enabled ?? stage.defaults.enabled);
	}

	const active = $derived(stages.filter(isOn));
	const phases = $derived([...new Set(stages.map((s) => s.phase))]);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="card" class:selected={isSelected} onclick={() => onEdit?.()}>
	<div class="body">
		<div class="top">
			{#if onSelect}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div class="select" class:on={isSelected} onclick={(e) => e.stopPropagation()}>
					<Checkbox
						checked={isSelected}
						onCheckedChange={() => onSelect()}
						aria-label="Select {engine.name}"
					/>
				</div>
			{/if}
			<div class="ident">
				<h3 class="name">{engine.name}</h3>
				<Badge variant="outline" class="intensity {badgeClass}">
					{INTENSITY_LABELS[engine.intensity]}
				</Badge>
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Badge
								{...props}
								variant="outline"
								class="intensity {summary.footprint === 'loud'
									? 'text-warning border-warning/30'
									: 'text-muted-foreground'}"
							>
								{#if summary.footprint === 'none'}<EyeOff size={10} />{/if}
								{FOOTPRINT_LABEL[summary.footprint]}
							</Badge>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content class="max-w-[240px] text-xs">
						{FOOTPRINT_HELP[summary.footprint]}
					</Tooltip.Content>
				</Tooltip.Root>
			</div>
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="actions" onclick={(e) => e.stopPropagation()}>
				<Button variant="ghost" size="icon-sm" aria-label="Run scan" onclick={() => onRun?.()}>
					<Play size={13} />
				</Button>
				<Button
					variant="ghost"
					size="icon-sm"
					aria-label="Duplicate"
					onclick={() => onDuplicate?.()}
				>
					<Copy size={13} />
				</Button>
				<Button
					variant="ghost"
					size="icon-sm"
					class="text-muted-foreground hover:text-destructive"
					aria-label="Delete"
					onclick={() => onDelete?.()}
				>
					<Trash2 size={13} />
				</Button>
			</div>
		</div>

		{#if engine.description}
			<p class="description">{engine.description}</p>
		{/if}

		<div class="phases">
			{#each phases as phase, i (phase)}
				{@const total = stages.filter((s) => s.phase === phase).length}
				{@const on = active.filter((s) => s.phase === phase).length}
				{#if i > 0}<ChevronRight size={11} class="arrow" />{/if}
				<span class="pill">
					<span class="pill-label">{phaseLabel(phase)}</span>
					<span class="pill-count">{on}/{total}</span>
				</span>
			{/each}
		</div>

		<div class="foot">
			<span>{summary.headline}</span>
			<span>
				{#if engine.usage?.schedules}
					{engine.usage.schedules} schedule{engine.usage.schedules === 1 ? '' : 's'}
				{:else if engine.last_used_at}
					Used {formatDistanceToNow(engine.last_used_at)}
				{:else}
					Never used
				{/if}
			</span>
		</div>
	</div>
</div>

<style>
	.card {
		display: flex;
		flex-direction: column;
		border: 1px solid var(--border);
		border-radius: 0.75rem;
		background: var(--card);
		cursor: pointer;
		transition:
			border-color 0.14s ease,
			background 0.14s ease;
	}
	.card:hover {
		border-color: color-mix(in oklch, var(--foreground) 22%, var(--border));
		background: color-mix(in oklch, var(--muted) 35%, var(--card));
	}
	.card.selected {
		border-color: color-mix(in oklch, var(--primary) 45%, var(--border));
		background: color-mix(in oklch, var(--primary) 6%, var(--card));
	}

	.select {
		display: flex;
		align-items: center;
		padding-top: 1px;
		opacity: 0;
		transition: opacity 0.14s ease;
	}
	.card:hover .select,
	.select.on,
	.select:focus-within {
		opacity: 1;
	}
	@media (hover: none) {
		.select {
			opacity: 1;
		}
	}

	.body {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 16px 18px;
	}

	.top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
	}
	.ident {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 7px;
		min-width: 0;
	}
	.name {
		font-size: 14px;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.ident :global(.intensity) {
		gap: 3px;
		font-size: 10px;
		font-weight: 400;
		padding: 1px 6px;
	}
	.actions {
		display: flex;
		gap: 1px;
		flex-shrink: 0;
	}

	.description {
		font-size: 12px;
		color: var(--muted-foreground);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.phases {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px;
	}
	.phases :global(.arrow) {
		color: var(--muted-foreground);
		opacity: 0.5;
	}
	.pill {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		height: 22px;
		padding: 0 8px;
		border-radius: 5px;
		background: var(--muted);
		font-size: 11px;
	}
	.pill-label {
		color: var(--muted-foreground);
	}
	.pill-count {
		font-variant-numeric: tabular-nums;
		font-weight: 500;
	}

	.foot {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding-top: 2px;
		font-size: 11px;
		color: var(--muted-foreground);
	}
</style>
