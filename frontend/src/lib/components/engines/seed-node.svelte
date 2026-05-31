<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { SEED_TYPES } from '$lib/types/engine';

	let { data }: NodeProps = $props();
</script>

<div class="seed-node">
	<div class="seed-header">
		<span class="seed-glyph">◎</span>
		<span class="seed-title">SEED TARGET</span>
	</div>

	<p class="seed-sub">Works with any target</p>

	<div class="seed-chips">
		{#each SEED_TYPES as t}
			<Badge variant="secondary" class="text-[10px] uppercase tracking-wide">{t}</Badge>
		{/each}
	</div>

	<Handle
		type="source"
		position={Position.Right}
		style="background: var(--muted-foreground); width: 8px; height: 8px; border: 2px solid var(--card); box-shadow: 0 1px 3px rgba(0,0,0,0.2);"
	/>
</div>

<style>
	.seed-node {
		width: 180px;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 12px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		user-select: none;
		cursor: default;
	}

	.seed-header {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.seed-glyph {
		font-size: 14px;
		line-height: 1;
		color: var(--muted-foreground);
	}

	.seed-title {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.06em;
		color: var(--foreground);
	}

	.seed-sub {
		margin: 0;
		font-size: 11px;
		color: var(--muted-foreground);
	}

	.seed-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
</style>
