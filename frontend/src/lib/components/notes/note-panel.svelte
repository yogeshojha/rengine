<script lang="ts">
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
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
		anchor?: NoteAnchor;
		filter: NoteFilter;
		showAnchor?: boolean;
		emptyTitle?: string;
		emptyDescription?: string;
		onCount?: (total: number) => void;
	}

	let {
		anchor,
		filter,
		showAnchor = true,
		emptyTitle = 'No notes',
		emptyDescription,
		onCount
	}: Props = $props();

	const PANEL_SIZE = 100;

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let items = $state<Note[]>([]);
	let total = $state(0);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let reqId = 0;

	async function load() {
		if (!projectId) return;
		const seq = ++reqId;
		loading = true;
		try {
			const page = await notes.list(projectId, { ...filter, size: PANEL_SIZE });
			if (seq !== reqId) return;
			items = page.items;
			total = page.total;
			error = null;
			onCount?.(page.total);
		} catch (e) {
			if (seq === reqId) {
				items = [];
				total = 0;
				error = e instanceof Error ? e.message : 'Notes not loaded.';
			}
		} finally {
			if (seq === reqId) loading = false;
		}
	}

	let loadedSignature = '';
	$effect(() => {
		const signature = JSON.stringify([projectId, filter, notes.version]);
		if (signature === loadedSignature) return;
		loadedSignature = signature;
		untrack(() => void load());
	});
</script>

<div class="flex flex-col">
	{#if anchor}
		<div class="border-b px-4 py-3">
			<NoteComposer {anchor} />
		</div>
	{/if}

	{#if loading && items.length === 0}
		<div class="flex flex-col gap-4 px-4 py-4" aria-busy="true">
			{#each Array(2) as _, i (i)}
				<div class="flex flex-col gap-2">
					<Skeleton class="h-3 w-32" />
					<Skeleton class="h-4 {i ? 'w-2/3' : 'w-full'}" />
				</div>
			{/each}
		</div>
	{:else if error}
		<EmptyState
			icon={TriangleAlert}
			title="Notes not loaded"
			description={error}
			compact
			class="border-0 bg-transparent"
		>
			<Button variant="outline" size="sm" onclick={() => void load()}>Retry</Button>
		</EmptyState>
	{:else if items.length === 0}
		<EmptyState
			icon={StickyNote}
			title={emptyTitle}
			description={emptyDescription}
			compact
			class="border-0 bg-transparent"
		/>
	{:else}
		<div class="divide-y">
			{#each items as note (note.id)}
				<NoteCard {note} {showAnchor} class="px-4" />
			{/each}
		</div>
		{#if total > items.length}
			<p class="border-t px-4 py-2 text-xs text-muted-foreground">
				Showing {items.length.toLocaleString()} of {total.toLocaleString()}
			</p>
		{/if}
	{/if}
</div>
