<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import Network from '@lucide/svelte/icons/network';
	import Layers from '@lucide/svelte/icons/layers';

	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import Hint from '$lib/components/hint.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import TreeNodeRow from './tree-node.svelte';
	import type { EndpointTree, TreeNode } from '$lib/utilities/endpoints';

	interface Props {
		tree: EndpointTree | null;
		loading?: boolean;
		mode: string;
		selected: string;
		onSelect: (node: TreeNode | null) => void;
		onMode: (mode: string) => void;
	}

	let { tree, loading = false, mode, selected, onSelect, onMode }: Props = $props();

	const expanded = new SvelteSet<string>();
	let autoKey = '';

	// open every root, then keep opening while a branch has exactly one way down
	$effect(() => {
		const key = tree?.nodes.map((n) => n.key).join('|') ?? '';
		if (!tree || key === autoKey) return;
		autoKey = key;
		expanded.clear();
		for (const root of tree.nodes.slice(0, 20)) {
			expanded.add(root.key);
			let cursor: TreeNode | undefined = root;
			while (cursor && cursor.children.length === 1) {
				cursor = cursor.children[0];
				expanded.add(cursor.key);
			}
		}
	});

	function toggle(key: string) {
		if (expanded.has(key)) expanded.delete(key);
		else expanded.add(key);
	}
</script>

<div class="flex h-full min-h-0 flex-col">
	<div class="flex items-center gap-2 border-b px-3 py-2">
		<span class="text-xs font-medium">Structure</span>
		{#if tree}
			<span class="text-xs tabular-nums text-muted-foreground">
				{tree.total_endpoints.toLocaleString()}
			</span>
		{/if}
		<ToggleGroup.Root
			type="single"
			value={mode}
			onValueChange={(v) => v && onMode(v)}
			class="ml-auto"
			size="sm"
		>
			<Hint text="One tree per host">
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<ToggleGroup.Item value="host" class="size-7" aria-label="Per host">
							<Network class="size-3.5" />
						</ToggleGroup.Item>
					</span>
				{/snippet}
			</Hint>
			<Hint text="Paths merged across every host, so a shared route appears once">
				{#snippet child(props)}
					<span {...props} class="inline-flex">
						<ToggleGroup.Item value="merged" class="size-7" aria-label="Across hosts">
							<Layers class="size-3.5" />
						</ToggleGroup.Item>
					</span>
				{/snippet}
			</Hint>
		</ToggleGroup.Root>
	</div>

	<ScrollArea class="min-h-0 flex-1">
		<div class="space-y-0.5 p-2">
			{#if loading && !tree}
				{#each Array(10) as _, i (i)}
					<Skeleton class="h-6 w-full" />
				{/each}
			{:else if !tree || tree.nodes.length === 0}
				<EmptyState
					title="No structure yet"
					description="Endpoints appear here once URL discovery has run."
				/>
			{:else}
				<button
					type="button"
					class="w-full rounded px-2 py-1 text-left text-xs {selected
						? 'text-muted-foreground hover:bg-muted/50'
						: 'bg-primary/10 font-medium text-primary'}"
					onclick={() => onSelect(null)}
				>
					Everything
					<span class="float-right tabular-nums">{tree.total_endpoints.toLocaleString()}</span>
				</button>
				{#each tree.nodes as node (node.key)}
					<TreeNodeRow
						{node}
						{expanded}
						{selected}
						onSelect={(n) => onSelect(n)}
						onToggle={toggle}
					/>
				{/each}
				{#if tree.truncated}
					<p class="px-2 pt-2 text-[11px] text-muted-foreground">
						The tree stops at {tree.total_nodes.toLocaleString()} folders. Narrow the search to see the
						rest.
					</p>
				{/if}
			{/if}
		</div>
	</ScrollArea>
</div>
