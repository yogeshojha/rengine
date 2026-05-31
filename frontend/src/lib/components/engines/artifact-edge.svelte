<script lang="ts">
	import { BaseEdge, EdgeLabel, getSmoothStepPath, type EdgeProps } from '@xyflow/svelte';
	import { ARTIFACT_COLOR, type ArtifactType } from '$lib/types/engine';

	interface ArtifactEdgeData extends Record<string, unknown> {
		artifact: ArtifactType;
		label: string;
		crossPhase: boolean;
		showLabel: boolean;
		animated: boolean;
	}

	let {
		sourceX,
		sourceY,
		sourcePosition,
		targetX,
		targetY,
		targetPosition,
		markerEnd,
		data
	}: EdgeProps = $props();

	let d = $derived(data as unknown as ArtifactEdgeData);

	// EdgeLabel renders into a separate container from .svelte-flow__edge, so a
	// :hover CSS selector on the edge can't reach the chip. Track hover locally
	// via the wide interaction path and drive the chip reveal from state.
	let hovered = $state(false);

	let path = $derived(
		getSmoothStepPath({
			sourceX,
			sourceY,
			sourcePosition,
			targetX,
			targetY,
			targetPosition,
			borderRadius: 14
		})
	);
	let edgePath = $derived(path[0]);
	let labelX = $derived(path[1]);
	let labelY = $derived(path[2]);

	let edgeClass = $derived(
		['artifact-edge-path', d.crossPhase ? 'cross-phase' : '', d.animated ? 'animated' : '']
			.filter(Boolean)
			.join(' ')
	);

	// cross-phase chips stay visible; intra-phase chips reveal on edge hover.
	let chipClass = $derived(
		['artifact-chip', d.crossPhase ? 'always' : 'on-hover', hovered ? 'edge-hovered' : '']
			.filter(Boolean)
			.join(' ')
	);

	// Artifact hue drives a subtle chip border/text accent on hover.
	let artifactColor = $derived(ARTIFACT_COLOR[d.artifact] ?? 'var(--border)');
</script>

<BaseEdge
	path={edgePath}
	{markerEnd}
	class={edgeClass}
	style="color: var(--muted-foreground);"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
/>

<EdgeLabel x={labelX} y={labelY}>
	<div class={chipClass} style="--artifact-color: {artifactColor};">{d.label}</div>
</EdgeLabel>

<style>
	/* Neutral, theme-aware wires. `color` is set on the element so currentColor
	   drives both the stroke and the arrowhead marker. */
	:global(.svelte-flow__edge .artifact-edge-path) {
		stroke: currentColor;
		stroke-width: 1.6px;
		opacity: 0.5;
		transition:
			opacity 0.16s ease,
			stroke-width 0.16s ease;
	}

	:global(.svelte-flow__edge .artifact-edge-path.cross-phase) {
		stroke-width: 2px;
		opacity: 0.7;
	}

	:global(.svelte-flow__edge .artifact-edge-path.animated) {
		opacity: 1;
		stroke-dasharray: 6 4;
		animation: artifact-dashdraw 0.5s linear infinite;
	}

	/* On hover the whole wire brightens to foreground for full legibility. */
	:global(.svelte-flow__edge:hover .artifact-edge-path) {
		color: var(--foreground);
		opacity: 1;
		stroke-width: 2.1px;
	}

	:global(.svelte-flow__edge:hover .artifact-edge-path.cross-phase) {
		stroke-width: 2.5px;
	}

	/* Arrowhead inherits the (now brighter) neutral edge color. */
	:global(.svelte-flow__edge marker path),
	:global(.svelte-flow__edge marker polyline) {
		fill: currentColor;
		stroke: currentColor;
	}

	@keyframes artifact-dashdraw {
		to {
			stroke-dashoffset: -10;
		}
	}

	.artifact-chip {
		display: inline-flex;
		align-items: center;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.375rem;
		padding: 0.125rem 0.375rem;
		font-size: 10px;
		line-height: 1.4;
		color: var(--muted-foreground);
		white-space: nowrap;
		/* Never block panning / node interaction. */
		pointer-events: none;
		transition:
			opacity 0.16s ease,
			color 0.16s ease,
			border-color 0.16s ease;
	}

	/* Intra-phase chips are calm by default, revealed when the edge is hovered. */
	.artifact-chip.on-hover {
		opacity: 0;
	}

	/* Hover reveals intra-phase chips and enriches every chip with the artifact hue.
	   The chip renders in a separate container from .svelte-flow__edge, so the
	   reveal is driven by the .edge-hovered class toggled from edge hover state. */
	.artifact-chip.edge-hovered {
		opacity: 1;
		color: var(--foreground);
		border-color: var(--artifact-color);
	}
</style>
