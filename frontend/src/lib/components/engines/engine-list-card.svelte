<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import Copy from '@lucide/svelte/icons/copy';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Network from '@lucide/svelte/icons/network';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import type { ScanEngine, Intensity } from '$lib/types/engine';
	import { PHASE_COLORS, INTENSITY_LABELS } from '$lib/types/engine';
	import { CAPABILITIES, getActiveCapabilities, type Phase } from '$lib/types/capabilities';
	import { formatDistanceToNow } from '$lib/utilities/dates';

	interface Props {
		engine: ScanEngine;
		onEdit?: () => void;
		onDuplicate?: () => void;
		onDelete?: () => void;
	}

	let { engine, onEdit, onDuplicate, onDelete }: Props = $props();

	const intensityClass: Record<Intensity, string> = {
		passive: 'text-muted-foreground border-border/60',
		normal: 'text-foreground border-border',
		aggressive: 'text-warning border-warning/30'
	};

	let badgeClass = $derived(intensityClass[engine.intensity] ?? intensityClass.normal);

	const PHASE_TOTAL: Record<Phase, number> = {
		discovery: CAPABILITIES.filter((c) => c.phase === 'discovery').length,
		expansion: CAPABILITIES.filter((c) => c.phase === 'expansion').length,
		depth: CAPABILITIES.filter((c) => c.phase === 'depth').length
	};

	let active = $derived(getActiveCapabilities(engine));

	let counts = $derived({
		discovery: active.filter((c) => c.phase === 'discovery').length,
		expansion: active.filter((c) => c.phase === 'expansion').length,
		depth: active.filter((c) => c.phase === 'depth').length
	});

	let totalActive = $derived(active.length);
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="card" onclick={() => onEdit?.()}>
	<div class="color-bar">
		<div style="flex:1; background:{PHASE_COLORS.discovery.accent};"></div>
		<div style="flex:1; background:{PHASE_COLORS.expansion.accent};"></div>
		<div style="flex:1; background:{PHASE_COLORS.depth.accent};"></div>
	</div>

	<div class="card-body">
		<div class="card-header">
			<div class="name-block">
				<h3 class="engine-name">{engine.name}</h3>
				<Badge variant="outline" class="intensity-badge {badgeClass}"
					>{INTENSITY_LABELS[engine.intensity]}</Badge
				>
			</div>
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="actions" onclick={(e) => e.stopPropagation()}>
				<Button variant="ghost" size="icon-sm" onclick={() => onDuplicate?.()}>
					<Copy size={13} />
				</Button>
				<Button
					variant="ghost"
					size="icon-sm"
					onclick={() => onDelete?.()}
					class="text-destructive hover:text-destructive"
				>
					<Trash2 size={13} />
				</Button>
			</div>
		</div>

		{#if engine.description}
			<p class="description">{engine.description}</p>
		{/if}

		<div class="phase-row">
			{#each [{ label: 'Discovery', count: counts.discovery, total: PHASE_TOTAL.discovery, color: PHASE_COLORS.discovery }, { label: 'Expansion', count: counts.expansion, total: PHASE_TOTAL.expansion, color: PHASE_COLORS.expansion }, { label: 'Depth', count: counts.depth, total: PHASE_TOTAL.depth, color: PHASE_COLORS.depth }] as phase, i (phase.label)}
				{#if i > 0}<ChevronRight size={11} class="phase-arrow" />{/if}
				<div class="phase-pill">
					<span class="phase-dot" style="background:{phase.color.accent};"></span>
					<span class="phase-pill-label" style="color:{phase.color.text};">{phase.label}</span>
					<span class="phase-count" style="color:{phase.color.accent};"
						>{phase.count}/{phase.total}</span
					>
				</div>
			{/each}
		</div>

		<div class="card-footer">
			<div class="footer-left">
				<Network size={12} class="footer-icon" />
				<span class="footer-stat"><strong>{totalActive}</strong> steps</span>
			</div>
			<div class="footer-right">
				{#if engine.updated_at}
					<span class="ts">Updated {formatDistanceToNow(engine.updated_at)}</span>
				{:else if engine.created_at}
					<span class="ts">Created {formatDistanceToNow(engine.created_at)}</span>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.card {
		border-radius: 10px;
		border: 1px solid var(--border);
		background: var(--card);
		overflow: hidden;
		box-shadow: var(--shadow-sm);
		transition:
			box-shadow 0.2s,
			transform 0.15s,
			border-color 0.2s;
		cursor: pointer;
	}

	.card:hover {
		box-shadow: var(--shadow-md);
		transform: translateY(-1px);
		border-color: var(--ring);
	}

	.color-bar {
		height: 3px;
		display: flex;
	}

	.card-body {
		padding: 14px 16px;
	}

	.card-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 10px;
		margin-bottom: 8px;
	}

	.name-block {
		display: flex;
		align-items: center;
		gap: 7px;
		flex-wrap: wrap;
		flex: 1;
		min-width: 0;
	}

	.engine-name {
		font-size: 14px;
		font-weight: 700;
		color: var(--foreground);
		margin: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	:global(.intensity-badge) {
		padding: 1px 8px;
		font-size: 10px;
		font-weight: 600;
		letter-spacing: 0.04em;
	}

	.actions {
		display: flex;
		align-items: center;
		gap: 2px;
		flex-shrink: 0;
	}

	.description {
		font-size: 12px;
		color: var(--muted-foreground);
		margin: 0 0 8px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.phase-row {
		display: flex;
		align-items: center;
		gap: 3px;
		margin-bottom: 12px;
		flex-wrap: wrap;
	}

	:global(.phase-arrow) {
		color: var(--muted-foreground);
		opacity: 0.5;
	}

	.phase-pill {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: 5px;
		background: var(--muted);
		border: 1px solid var(--border);
	}

	.phase-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.phase-pill-label {
		font-size: 10px;
		font-weight: 600;
	}

	.phase-count {
		font-size: 10px;
		font-weight: 500;
	}

	.card-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-top: 10px;
		border-top: 1px solid var(--border);
	}

	.footer-left {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	:global(.footer-icon) {
		color: var(--muted-foreground);
	}

	.footer-stat {
		font-size: 11px;
		color: var(--muted-foreground);
	}

	.footer-stat strong {
		color: var(--foreground);
	}

	.footer-right {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.ts {
		font-size: 11px;
		color: var(--muted-foreground);
	}
</style>
