<script lang="ts">
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import { Button } from '$lib/components/ui/button';
	import NotesDialog from './notes-dialog.svelte';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { cn } from '$lib/utils';
	import type { NoteAnchor } from '$lib/types/note';

	interface Props {
		anchor: NoteAnchor;
		class?: string;
	}

	let { anchor, class: className }: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let dimension = $derived(anchor.dimension ?? null);
	let assetKey = $derived(anchor.assetKey ?? null);
	let total = $state<number | null>(null);
	let open = $state(false);
	let count = $derived(total ?? 0);

	$effect(() => {
		void dimension;
		void assetKey;
		total = null;
		open = false;
	});

	$effect(() => {
		void notes.version;
		const id = projectId;
		const dim = dimension;
		const key = assetKey;
		if (!id || !dim || !key) return;
		let live = true;
		notes
			.list(id, { dimension: dim, asset_key: key, size: 1 })
			.then((page) => {
				if (live) total = page.total;
			})
			.catch(() => {
				if (live) total = null;
			});
		return () => {
			live = false;
		};
	});
</script>

{#if dimension && assetKey}
	<Button
		variant="ghost"
		size="sm"
		class={cn('h-7 gap-1.5 px-2 text-xs', className)}
		onclick={() => (open = true)}
	>
		<StickyNote class="size-3.5" />
		{#if count > 0}
			Notes
			<span class="text-muted-foreground tabular-nums">{count.toLocaleString()}</span>
		{:else}
			Add note
		{/if}
	</Button>
	<NotesDialog bind:open {anchor} expected={total ?? 0} onCount={(n) => (total = n)} />
{/if}
