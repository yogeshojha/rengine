<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	// Invisible 1x1 routing point. Lives in the empty gutter between two phase
	// bands so inter-phase connector edges anchor here and never cross a node.
</script>

<div class="gutter-anchor" aria-hidden="true">
	<Handle type="target" position={Position.Left} class="anchor-handle" />
	<Handle type="source" position={Position.Right} class="anchor-handle" />
</div>

<style>
	.gutter-anchor {
		width: 1px;
		height: 1px;
		opacity: 0;
		pointer-events: none;
	}
	.gutter-anchor :global(.anchor-handle) {
		width: 1px;
		height: 1px;
		min-width: 0;
		min-height: 0;
		border: none;
		background: transparent;
		opacity: 0;
	}
</style>
