<script lang="ts">
	import { Handle, Position, type NodeProps } from '@xyflow/svelte';
	import Database from '@lucide/svelte/icons/database';
	import Globe from '@lucide/svelte/icons/globe';
	import Share2 from '@lucide/svelte/icons/share-2';
	import Search from '@lucide/svelte/icons/search';
	import Radar from '@lucide/svelte/icons/radar';
	import Globe2 from '@lucide/svelte/icons/globe-2';
	import Cpu from '@lucide/svelte/icons/cpu';
	import Camera from '@lucide/svelte/icons/camera';
	import Unlink from '@lucide/svelte/icons/unlink';
	import Cloud from '@lucide/svelte/icons/cloud';
	import Compass from '@lucide/svelte/icons/compass';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import FileText from '@lucide/svelte/icons/file-text';
	import type { ReconOutput } from '$lib/types/capabilities';

	interface ReconNodeData extends Record<string, unknown> {
		outputs: ReconOutput[];
	}

	let { data }: NodeProps = $props();
	let d = $derived(data as unknown as ReconNodeData);

	const MAX_ROWS = 8;
	let shown = $derived(d.outputs.slice(0, MAX_ROWS));
	let overflow = $derived(Math.max(0, d.outputs.length - MAX_ROWS));
</script>

<div class="recon-node">
	<span class="accent-rail" aria-hidden="true"></span>

	<div class="recon-head">
		<div class="icon-chip"><Database size={15} /></div>
		<div class="recon-titles">
			<span class="recon-title">RECON DATA</span>
			<span class="recon-sub">final results</span>
		</div>
	</div>

	<div class="recon-body">
		{#each shown as o (o.key)}
			<div class="recon-row">
				<span class="row-icon">
					{#if o.icon === 'Globe'}
						<Globe size={13} />
					{:else if o.icon === 'Share2'}
						<Share2 size={13} />
					{:else if o.icon === 'Search'}
						<Search size={13} />
					{:else if o.icon === 'Radar'}
						<Radar size={13} />
					{:else if o.icon === 'Globe2'}
						<Globe2 size={13} />
					{:else if o.icon === 'Cpu'}
						<Cpu size={13} />
					{:else if o.icon === 'Camera'}
						<Camera size={13} />
					{:else if o.icon === 'Unlink'}
						<Unlink size={13} />
					{:else if o.icon === 'Cloud'}
						<Cloud size={13} />
					{:else if o.icon === 'Compass'}
						<Compass size={13} />
					{:else if o.icon === 'SlidersHorizontal'}
						<SlidersHorizontal size={13} />
					{:else if o.icon === 'KeyRound'}
						<KeyRound size={13} />
					{:else if o.icon === 'ShieldAlert'}
						<ShieldAlert size={13} />
					{:else if o.icon === 'FileText'}
						<FileText size={13} />
					{:else}
						<Globe size={13} />
					{/if}
				</span>
				<span class="row-label">{o.label}</span>
			</div>
		{/each}
		{#if overflow > 0}
			<div class="recon-row more">+{overflow} more</div>
		{/if}
	</div>

	<Handle
		type="target"
		position={Position.Left}
		style="background: var(--muted-foreground); width: 9px; height: 9px; border: 2px solid var(--card);"
	/>
</div>

<style>
	.recon-node {
		position: relative;
		width: 220px;
		background: var(--card);
		border: 1px solid var(--border);
		border-radius: 0.75rem;
		box-shadow: var(--shadow-xs);
		overflow: hidden;
		user-select: none;
		cursor: default;
	}

	.accent-rail {
		position: absolute;
		top: 0;
		left: 0;
		bottom: 0;
		width: 2px;
		background: var(--primary);
	}

	.recon-head {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 12px 8px 14px;
		border-bottom: 1px solid var(--border);
	}
	.icon-chip {
		width: 28px;
		height: 28px;
		flex-shrink: 0;
		border-radius: 7px;
		background: var(--secondary);
		color: var(--foreground);
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.recon-titles {
		display: flex;
		flex-direction: column;
		min-width: 0;
		line-height: 1.1;
	}
	.recon-title {
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.06em;
		color: var(--foreground);
	}
	.recon-sub {
		font-size: 10px;
		color: var(--muted-foreground);
		margin-top: 2px;
	}

	.recon-body {
		display: flex;
		flex-direction: column;
		padding: 6px 12px 10px 14px;
		gap: 2px;
	}
	.recon-row {
		display: flex;
		align-items: center;
		gap: 7px;
		padding: 2px 0;
	}
	.row-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--muted-foreground);
		flex-shrink: 0;
	}
	.row-label {
		font-size: 12px;
		color: var(--foreground);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.recon-row.more {
		font-size: 11px;
		color: var(--muted-foreground);
		padding-left: 20px;
	}
</style>
