<script lang="ts">
	import type { Snippet } from 'svelte';
	import {
		SvelteFlow,
		Background,
		Controls,
		BackgroundVariant,
		useSvelteFlow
	} from '@xyflow/svelte';

	interface Props {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		nodes: any[];
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		edges: any[];
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		nodeTypes: any;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		edgeTypes: any;
		fitKey: number;
		fitNonce?: number;
		onNodePointerEnter?: (e: { node: { id: string } }) => void;
		onNodePointerLeave?: () => void;
		children?: Snippet;
	}

	let {
		nodes = $bindable(),
		edges = $bindable(),
		nodeTypes,
		edgeTypes,
		fitKey,
		fitNonce = 0,
		onNodePointerEnter,
		onNodePointerLeave,
		children
	}: Props = $props();

	const { fitView } = useSvelteFlow();
	$effect(() => {
		void fitKey;
		void fitNonce;
		queueMicrotask(() => fitView({ duration: 250, padding: 0.1 }));
	});
</script>

<SvelteFlow
	bind:nodes
	bind:edges
	{nodeTypes}
	{edgeTypes}
	defaultEdgeOptions={{ type: 'artifact' }}
	nodesConnectable={false}
	fitView
	fitViewOptions={{ padding: 0.1 }}
	minZoom={0.2}
	maxZoom={2}
	colorMode="system"
	proOptions={{ hideAttribution: true }}
	onnodepointerenter={onNodePointerEnter}
	onnodepointerleave={onNodePointerLeave}
>
	<Background variant={BackgroundVariant.Dots} gap={22} size={1} />
	<Controls showZoom showFitView showLock={false} position="bottom-left" />
	{@render children?.()}
</SvelteFlow>

<style>
	:global(.svelte-flow) {
		--xy-edge-stroke-default: var(--muted-foreground);
		--xy-handle-background-color-default: var(--muted-foreground);
		--xy-handle-border-color-default: var(--card);
		--xy-controls-button-background-color-default: var(--card);
		--xy-controls-button-color-default: var(--muted-foreground);
		--xy-controls-button-border-color-default: var(--border);
		--xy-background-pattern-color: var(--border);
		--xy-node-boxshadow-hover-default: none;
	}

	:global(.svelte-flow__viewport-back) {
		z-index: 0;
	}
	:global(.svelte-flow__edges) {
		z-index: 2;
		overflow: visible;
	}
	:global(.svelte-flow__nodes) {
		z-index: 3;
	}
	:global(.svelte-flow__edge-labels) {
		z-index: 4;
	}

	:global(.svelte-flow__edge .svelte-flow__edge-path) {
		stroke: var(--muted-foreground);
	}
	:global(.svelte-flow__arrowclosed),
	:global(.svelte-flow__edge marker path),
	:global(.svelte-flow__edge marker polyline) {
		fill: var(--muted-foreground);
		stroke: var(--muted-foreground);
	}
</style>
