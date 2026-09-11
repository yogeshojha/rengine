<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import * as Collapsible from '$lib/components/ui/collapsible';
	import NotePanel from './note-panel.svelte';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { NoteAnchor } from '$lib/types/note';

	interface Props {
		anchor: NoteAnchor;
	}

	let { anchor }: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let open = $state(false);
	let total = $state<number | null>(null);
	let composerOpen = $state(false);

	let filter = $derived({
		dimension: anchor.dimension ?? undefined,
		asset_key: anchor.assetKey ?? undefined
	});

	$effect(() => {
		const key = anchor.assetKey;
		if (!key) return;
		open = false;
		total = null;
	});

	$effect(() => {
		if (!projectId || !anchor.assetKey || !anchor.dimension) return;
		void notes
			.list(projectId, { ...filter, size: 1 })
			.then((page) => (total = page.total))
			.catch(() => (total = null));
	});
</script>

{#if anchor.assetKey && anchor.dimension}
	<Collapsible.Root bind:open>
		<Collapsible.Trigger
			class="flex w-full items-center gap-2 py-2 text-sm font-medium hover:text-foreground"
		>
			<ChevronRight
				class="size-4 shrink-0 text-muted-foreground transition-transform {open ? 'rotate-90' : ''}"
			/>
			<StickyNote class="size-4 shrink-0 text-muted-foreground" />
			Notes
			{#if total}
				<span class="text-xs text-muted-foreground tabular-nums">{total.toLocaleString()}</span>
			{/if}
		</Collapsible.Trigger>
		<Collapsible.Content>
			<div class="overflow-hidden rounded-lg border">
				<NotePanel
					{anchor}
					{filter}
					showAnchor={false}
					bind:composerOpen
					emptyTitle="No notes"
					emptyDescription="Notes written on this asset appear here."
					onCount={(n) => (total = n)}
				/>
			</div>
		</Collapsible.Content>
	</Collapsible.Root>
{/if}
