<script lang="ts">
	import { untrack } from 'svelte';
	import Search from '@lucide/svelte/icons/search';
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import X from '@lucide/svelte/icons/x';
	import * as Card from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import NoteCard from '$lib/components/notes/note-card.svelte';
	import { notes } from '$lib/stores/notes.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import type { Note, NoteStatus } from '$lib/types/note';

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let projectSlug = $derived(projectsStore.activeProject?.slug ?? '');

	let items = $state<Note[]>([]);
	let total = $state(0);
	let loading = $state(false);
	let search = $state('');
	let statusTab = $state<'all' | NoteStatus>('open');
	let dimension = $state<string | null>(null);
	let tagIds = $state<string[]>([]);
	let counts = $state<Record<string, number>>({ all: 0, open: 0, resolved: 0 });
	let reqId = 0;
	let timer: ReturnType<typeof setTimeout> | null = null;

	const STATUS_TABS = [
		{ key: 'open', label: 'Open' },
		{ key: 'resolved', label: 'Resolved' },
		{ key: 'all', label: 'All' }
	];

	$effect(() => {
		if (projectSlug && projectId) void notes.loadTags(projectSlug, projectId);
	});

	async function load() {
		if (!projectId) return;
		const seq = ++reqId;
		loading = true;
		try {
			const [page, open, resolved] = await Promise.all([
				notes.list(projectId, {
					search: search.trim() || undefined,
					status: statusTab === 'all' ? undefined : [statusTab],
					dimension: dimension ?? undefined,
					tag: tagIds.length ? tagIds : undefined,
					size: 100
				}),
				notes.list(projectId, { status: ['open'], size: 1 }),
				notes.list(projectId, { status: ['resolved'], size: 1 })
			]);
			if (seq !== reqId) return;
			items = page.items;
			total = page.total;
			counts = {
				open: open.total,
				resolved: resolved.total,
				all: open.total + resolved.total
			};
		} catch {
			if (seq === reqId) items = [];
		} finally {
			if (seq === reqId) loading = false;
		}
	}

	$effect(() => {
		const signature = JSON.stringify([projectId, statusTab, dimension, tagIds, search]);
		void signature;
		untrack(() => {
			if (timer) clearTimeout(timer);
			timer = setTimeout(() => void load(), search ? 250 : 0);
		});
	});

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

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Notes</h1>
		<p class="mt-1 text-sm text-muted-foreground">
			Everything written down against an asset in this project.
		</p>
	</div>

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
			<div class="flex flex-col gap-2 px-4 py-4">
				{#each Array(4) as _, i (i)}
					<Skeleton class="h-16 w-full" />
				{/each}
			</div>
		{:else if items.length === 0}
			<EmptyState
				icon={StickyNote}
				title={filtered ? 'No notes match' : 'No notes yet'}
				description={filtered
					? 'Change the filters to widen the search.'
					: 'Notes are written from an asset in a scan result.'}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else}
			<div class="transition-opacity {loading ? 'opacity-60' : ''}">
				{#each items as note (note.id)}
					<NoteCard {note} onChanged={load} />
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
