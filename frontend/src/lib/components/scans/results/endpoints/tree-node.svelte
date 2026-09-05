<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Folder from '@lucide/svelte/icons/folder';
	import Globe from '@lucide/svelte/icons/globe';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';

	import Hint from '$lib/components/hint.svelte';
	import StatusBar from './status-bar.svelte';
	import Self from './tree-node.svelte';
	import { INTEREST_LABELS, SENSITIVE_INTEREST } from '$lib/config/endpoints';
	import type { TreeNode } from '$lib/utilities/endpoints';

	interface Props {
		node: TreeNode;
		expanded: Set<string>;
		selected: string;
		depth?: number;
		onSelect: (node: TreeNode) => void;
		onToggle: (key: string) => void;
	}

	let { node, expanded, selected, depth = 0, onSelect, onToggle }: Props = $props();

	let open = $derived(expanded.has(node.key));
	let isHost = $derived(node.kind === 'host');
	let active = $derived(selected === node.key);
	let sensitive = $derived(node.interest.filter((i) => SENSITIVE_INTEREST.has(i)));
</script>

<div>
	<div
		class="group flex items-center gap-1 rounded px-1 py-1 text-sm {active
			? 'bg-primary/10 text-primary'
			: 'hover:bg-muted/50'}"
		style="padding-left:{depth * 12 + 4}px"
	>
		<button
			type="button"
			class="flex size-4 shrink-0 items-center justify-center rounded text-muted-foreground hover:text-foreground {node.child_count
				? ''
				: 'invisible'}"
			aria-label={open ? 'Collapse' : 'Expand'}
			onclick={(e) => {
				e.stopPropagation();
				onToggle(node.key);
			}}
		>
			<ChevronRight class="size-3.5 transition-transform {open ? 'rotate-90' : ''}" />
		</button>

		<button
			type="button"
			class="flex min-w-0 flex-1 items-center gap-1.5 text-left"
			onclick={() => onSelect(node)}
		>
			<span class="flex h-5 shrink-0 items-center text-muted-foreground">
				{#if isHost}
					<Globe class="size-3.5" />
				{:else}
					<Folder class="size-3.5" />
				{/if}
			</span>
			<span class="truncate font-mono text-xs {isHost ? 'font-medium' : ''}">{node.name}</span>
			{#if sensitive.length}
				<Hint text={sensitive.map((k) => INTEREST_LABELS[k] ?? k).join(', ')}>
					{#snippet child(props)}
						<span {...props} class="flex h-5 shrink-0 items-center text-destructive">
							<ShieldAlert class="size-3" />
						</span>
					{/snippet}
				</Hint>
			{/if}
			<span class="ml-auto shrink-0 text-[10px] tabular-nums text-muted-foreground">
				{node.subtree_count}
			</span>
		</button>
	</div>

	<div class="pr-1" style="padding-left:{depth * 12 + 26}px">
		<StatusBar mix={node.status_mix} total={node.subtree_count} />
	</div>

	{#if open}
		{#each node.children as child (child.key)}
			<Self node={child} {expanded} {selected} depth={depth + 1} {onSelect} {onToggle} />
		{/each}
	{/if}
</div>
