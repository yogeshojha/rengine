<script lang="ts">
	import { BaseEdge, EdgeLabel, getSmoothStepPath, type EdgeProps } from '@xyflow/svelte';
	import { type ArtifactType } from '$lib/types/engine';

	interface ArtifactEdgeData extends Record<string, unknown> {
		artifact: ArtifactType;
		label: string;
		crossPhase: boolean;
		alwaysLabel: boolean;
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

	let chipClass = $derived(
		[
			'artifact-chip',
			'nodrag',
			'nopan',
			d.alwaysLabel ? 'always' : 'on-hover',
			hovered ? 'edge-hovered' : ''
		]
			.filter(Boolean)
			.join(' ')
	);
</script>

<BaseEdge
	path={edgePath}
	{markerEnd}
	class={edgeClass}
	style="color: var(--muted-foreground);"
	onmouseenter={() => (hovered = true)}
	onmouseleave={() => (hovered = false)}
/>

<EdgeLabel x={labelX} y={labelY} transparent>
	<div class={chipClass}>{d.label}</div>
</EdgeLabel>

<style>
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

	:global(.svelte-flow__edge:hover .artifact-edge-path) {
		color: var(--foreground);
		opacity: 1;
		stroke-width: 2.1px;
	}

	:global(.svelte-flow__edge:hover .artifact-edge-path.cross-phase) {
		stroke-width: 2.5px;
	}

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
		transform: translateY(-9px);
		pointer-events: none;
		transition:
			opacity 0.16s ease,
			color 0.16s ease,
			border-color 0.16s ease;
	}

	.artifact-chip.always {
		color: var(--foreground);
		font-weight: 500;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.14);
	}

	.artifact-chip.on-hover {
		opacity: 0;
	}

	.artifact-chip.edge-hovered {
		opacity: 1;
		color: var(--foreground);
		border-color: var(--ring);
	}
</style>
