<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Button } from '$lib/components/ui/button';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Separator } from '$lib/components/ui/separator';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import EmptyState from '$lib/components/empty-state.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import { DiscardGuard } from '$lib/utilities/discard-guard.svelte';
	import NoteCard from './note-card.svelte';
	import NoteComposer from './note-composer.svelte';
	import { holdSheetKeys } from './keys';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import type { Note, NoteAnchor } from '$lib/types/note';

	interface Props {
		open: boolean;
		anchor: NoteAnchor;
		expected?: number;
		onCount?: (total: number) => void;
	}

	let { open = $bindable(false), anchor, expected = 0, onCount }: Props = $props();

	const THREAD_SIZE = 100;

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let dimension = $derived(anchor.dimension ?? null);
	let assetKey = $derived(anchor.assetKey ?? null);
	let label = $derived(anchor.assetLabel || anchor.assetKey || '');
	let items = $state<Note[]>([]);
	let total = $state(0);
	let loaded = $state(false);
	let error = $state<string | null>(null);
	let reqId = 0;
	let composer = $state<ReturnType<typeof NoteComposer> | null>(null);
	const dirtyNotes = new SvelteSet<string>();

	let showThread = $derived(items.length > 0 || !!error || (!loaded && expected > 0));

	const guard = new DiscardGuard(
		() => (composer?.dirty() ?? false) || dirtyNotes.size > 0,
		() => (open = false)
	);

	async function load() {
		if (!projectId || !dimension || !assetKey) return;
		const seq = ++reqId;
		try {
			const page = await notes.list(projectId, {
				dimension,
				asset_key: assetKey,
				size: THREAD_SIZE
			});
			if (seq !== reqId) return;
			items = page.items;
			total = page.total;
			error = null;
			loaded = true;
			onCount?.(page.total);
		} catch (e) {
			if (seq === reqId) error = e instanceof Error ? e.message : 'Notes not loaded.';
		}
	}

	$effect(() => {
		void dimension;
		void assetKey;
		reqId++;
		items = [];
		total = 0;
		loaded = false;
		error = null;
	});

	$effect(() => {
		void notes.version;
		if (open && projectId && dimension && assetKey) untrack(() => void load());
	});
</script>

<Dialog.Root bind:open={() => open, (next) => (next ? (open = true) : guard.close())}>
	<Dialog.Content
		class="flex max-h-[85vh] flex-col gap-4 sm:max-w-xl"
		onOpenAutoFocus={(e) => {
			e.preventDefault();
			requestAnimationFrame(() => composer?.focus());
		}}
		onkeydown={holdSheetKeys}
	>
		<Dialog.Header class="min-w-0 pr-6">
			<Dialog.Title>Notes</Dialog.Title>
			{#if label}
				<Dialog.Description class="truncate font-mono text-xs">{label}</Dialog.Description>
			{/if}
		</Dialog.Header>

		<div class="shrink-0">
			{#key assetKey}
				<NoteComposer bind:this={composer} {anchor} autofocus />
			{/key}
		</div>

		{#if showThread}
			<div class="flex min-h-0 flex-col">
				<Separator />
				{#if error}
					<EmptyState
						compact
						icon={TriangleAlert}
						title="Notes not loaded"
						description={error}
						class="border-0 bg-transparent"
					>
						<Button variant="outline" size="sm" onclick={() => void load()}>Retry</Button>
					</EmptyState>
				{:else if !loaded}
					<div class="flex flex-col gap-5 pt-4" aria-busy="true">
						{#each Array(2) as _, i (i)}
							<div class="flex flex-col gap-2">
								<Skeleton class="h-3 w-32" />
								<Skeleton class="h-4 {i ? 'w-2/3' : 'w-full'}" />
							</div>
						{/each}
					</div>
				{:else}
					<ScrollArea
						class="-mx-6 -mb-3 min-h-0 [&_[data-slot=scroll-area-viewport]]:max-h-[min(28rem,calc(85vh-20rem))]"
					>
						<div class="divide-y px-6">
							{#each items as note (note.id)}
								<NoteCard
									{note}
									showAnchor={false}
									onDirty={(dirty) =>
										dirty ? dirtyNotes.add(note.id) : dirtyNotes.delete(note.id)}
								/>
							{/each}
						</div>
						{#if total > items.length}
							<p class="px-6 pb-3 text-xs text-muted-foreground">
								Showing {items.length.toLocaleString()} of {total.toLocaleString()}
							</p>
						{/if}
					</ScrollArea>
				{/if}
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<UnsavedChangesDialog
	open={guard.asking}
	onOpenChange={(next) => (guard.asking = next)}
	onConfirm={guard.discard}
/>
