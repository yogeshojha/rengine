<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
	import { untrack } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import X from '@lucide/svelte/icons/x';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import NoteCard from '$lib/components/notes/note-card.svelte';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import { notesApi } from '$lib/api/notes';
	import { SvelteSet } from 'svelte/reactivity';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import { NOTE_STATUS_LABELS, NOTE_STATUSES, type Note, type NoteStatus } from '$lib/types/note';

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let projectSlug = $derived(projectsStore.activeProject?.slug ?? '');

	let items = $state<Note[]>([]);
	let total = $state(0);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let search = $state('');
	let statusTab = $state<'all' | NoteStatus>('open');
	let dimension = $state<string | null>(null);
	let tagIds = $state<string[]>([]);
	let counts = $state<Record<string, number>>({ all: 0, open: 0, resolved: 0 });
	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;
	const picked = new SvelteSet<string>();

	const STATUS_TABS = [
		...NOTE_STATUSES.map((status) => ({ key: status, label: NOTE_STATUS_LABELS[status] })),
		{ key: 'all', label: 'All' }
	];

	$effect(() => {
		if (projectSlug && projectId) void notes.loadTags(projectSlug, projectId);
	});

	async function loadPage() {
		if (!projectId) return;
		const seq = ++reqId;
		loading = true;
		try {
			const page = await notes.list(projectId, {
				search: search.trim() || undefined,
				status: statusTab === 'all' ? undefined : [statusTab],
				dimension: dimension ?? undefined,
				tag: tagIds.length ? tagIds : undefined,
				size: 100
			});
			if (seq !== reqId) return;
			items = page.items;
			total = page.total;
			error = null;
		} catch (e) {
			if (seq === reqId) error = e instanceof Error ? e.message : 'Notes not loaded';
		} finally {
			if (seq === reqId) loading = false;
		}
	}

	// the tab totals depend on the project alone, never on the filters
	async function loadCounts() {
		if (!projectId) return;
		const id = projectId;
		try {
			const [open, resolved] = await Promise.all([
				notes.list(id, { status: ['open'], size: 1 }),
				notes.list(id, { status: ['resolved'], size: 1 })
			]);
			if (id !== projectId) return;
			counts = { open: open.total, resolved: resolved.total, all: open.total + resolved.total };
		} catch {
			/* the tab totals keep their last good value */
		}
	}

	function reload() {
		void loadPage();
		void loadCounts();
	}

	$effect(() => {
		const id = projectId;
		if (id) untrack(() => void loadCounts());
	});

	$effect(() => {
		const signature = JSON.stringify([projectId, statusTab, dimension, tagIds, search]);
		void signature;
		untrack(() => {
			if (timer) clearTimeout(timer);
			timer = setTimeout(() => void loadPage(), search ? 250 : 0);
		});
	});

	function toggleCheck(id: string) {
		if (picked.has(id)) picked.delete(id);
		else picked.add(id);
	}

	function toggleTag(id: string) {
		tagIds = tagIds.includes(id) ? tagIds.filter((t) => t !== id) : [...tagIds, id];
	}

	let filtered = $derived(Boolean(search.trim()) || dimension !== null || tagIds.length > 0);

	function clearFilters() {
		search = '';
		dimension = null;
		tagIds = [];
	}
</script>

<svelte:head><title>{routeLabels.notes} · reNgine</title></svelte:head>

<div class="space-y-6">
	<h1 class="text-2xl font-semibold tracking-tight">Notes</h1>

	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="border-b px-2">
			<CountTabs
				tabs={STATUS_TABS}
				value={statusTab}
				{counts}
				onChange={(k) => (statusTab = k as 'all' | NoteStatus)}
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
			<div class="relative min-w-56 flex-1">
				<Search
					class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground"
				/>
				<Input bind:value={search} placeholder="Search notes" class="h-8 pl-8 text-sm" />
			</div>
			<div class="flex flex-wrap items-center gap-1">
				{#each SURFACE_ORDER as spec (spec.key)}
					<button
						type="button"
						class="rounded-md border px-2 py-1 text-xs transition-colors {dimension === spec.key
							? 'border-primary/40 bg-primary/10 text-foreground'
							: 'bg-background text-muted-foreground hover:text-foreground'}"
						onclick={() => (dimension = dimension === spec.key ? null : spec.key)}
					>
						{spec.label}
					</button>
				{/each}
			</div>
		</div>

		{#if notes.tags.length > 0}
			<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
				{#each notes.tags as tag (tag.id)}
					<button
						type="button"
						class="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs transition-colors {tagIds.includes(
							tag.id
						)
							? 'border-primary/40 bg-primary/10 text-foreground'
							: 'bg-background text-muted-foreground hover:text-foreground'}"
						onclick={() => toggleTag(tag.id)}
						aria-pressed={tagIds.includes(tag.id)}
					>
						<span class="size-2 shrink-0 rounded-full" style="background-color: {tag.color}"></span>
						{tag.name}
					</button>
				{/each}
				{#if filtered}
					<button
						class="ml-1 inline-flex items-center gap-1 rounded-sm text-xs text-muted-foreground hover:text-foreground"
						onclick={clearFilters}
					>
						<X class="size-3" />
						Clear filters
					</button>
				{/if}
			</div>
		{/if}

		{#if loading && items.length === 0}
			<RowSkeleton rows={5} avatar="size-8 rounded-md" trailing="h-3.5 w-20" />
		{:else if error}
			<EmptyState
				icon={StickyNote}
				title="Notes not loaded"
				description={error}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else if items.length === 0}
			<EmptyState
				icon={StickyNote}
				title={filtered ? 'No notes match' : 'No notes'}
				description={filtered ? 'Clear a filter.' : 'Add a note from an asset in a scan result.'}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else}
			<div class="transition-opacity {loading ? 'opacity-60' : ''}">
				{#each items as note (note.id)}
					<NoteCard {note} checked={picked.has(note.id)} onCheck={toggleCheck} onChanged={reload} />
				{/each}
			</div>
			{#if total > items.length}
				<div class="border-t px-4 py-2 text-xs text-muted-foreground">
					Showing {items.length.toLocaleString()} of {total.toLocaleString()}
				</div>
			{/if}
		{/if}
	</Card.Root>
</div>

<SelectionDeleteBar
	ids={[...picked]}
	noun="note"
	remove={(id) => notesApi.remove(projectId, id)}
	onDone={() => {
		picked.clear();
		reload();
	}}
	onClear={() => picked.clear()}
/>
