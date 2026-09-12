<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import { untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import NoteCard from './note-card.svelte';
	import NoteComposer from './note-composer.svelte';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { Note, NoteAnchor, NoteFilter } from '$lib/types/note';

	interface Props {
		anchor: NoteAnchor;
		filter: NoteFilter;
		showAnchor?: boolean;
		emptyTitle?: string;
		emptyDescription?: string;
		composerOpen?: boolean;
		onCount?: (total: number) => void;
	}

	let {
		anchor,
		filter,
		showAnchor = true,
		emptyTitle = 'No notes',
		emptyDescription,
		composerOpen = $bindable(false),
		onCount
	}: Props = $props();

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let items = $state<Note[]>([]);
	let total = $state(0);
	let loading = $state(false);
	let reqId = 0;

	async function load() {
		if (!projectId) return;
		const seq = ++reqId;
		loading = true;
		try {
			const page = await notes.list(projectId, { ...filter, size: 100 });
			if (seq !== reqId) return;
			items = page.items;
			total = page.total;
			onCount?.(page.total);
		} catch {
			if (seq === reqId) items = [];
		} finally {
			if (seq === reqId) loading = false;
		}
	}

	$effect(() => {
		const signature = JSON.stringify([projectId, filter]);
		void signature;
		untrack(() => void load());
	});
</script>

<div class="flex flex-col">
	<div class="flex items-center justify-between gap-2 px-4 py-2.5">
		<span class="text-xs font-medium text-muted-foreground">
			{total === 1 ? '1 note' : `${total.toLocaleString()} notes`}
		</span>
		{#if !composerOpen}
			<Button
				variant="outline"
				size="sm"
				class="h-7 gap-1.5 px-2"
				onclick={() => (composerOpen = true)}
			>
				<Plus class="size-3.5" />
				Add note
			</Button>
		{/if}
	</div>

	{#if composerOpen}
		<div class="border-y bg-muted/20 px-4 py-3">
			<NoteComposer
				{anchor}
				autofocus
				onSaved={() => {
					composerOpen = false;
					void load();
				}}
				onCancel={() => (composerOpen = false)}
			/>
		</div>
	{/if}

	{#if loading && items.length === 0}
		<div class="flex flex-col gap-2 px-4 py-3">
			{#each Array(2) as _, i (i)}
				<Skeleton class="h-12 w-full" />
			{/each}
		</div>
	{:else if items.length === 0}
		<EmptyState
			icon={StickyNote}
			title={emptyTitle}
			description={emptyDescription}
			class="border-0 bg-transparent py-10"
		/>
	{:else}
		<div class="border-t">
			{#each items as note (note.id)}
				<NoteCard {note} {showAnchor} onChanged={load} />
			{/each}
		</div>
	{/if}
</div>
