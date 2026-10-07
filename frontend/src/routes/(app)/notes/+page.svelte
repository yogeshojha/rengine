<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	import Search from '@lucide/svelte/icons/search';
	import StickyNote from '@lucide/svelte/icons/sticky-note';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import X from '@lucide/svelte/icons/x';
	import ListFilter from '@lucide/svelte/icons/list-filter';
	import * as Card from '$lib/components/ui/card';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Button } from '$lib/components/ui/button';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Badge } from '$lib/components/ui/badge';
	import * as Popover from '$lib/components/ui/popover';
	import EmptyState from '$lib/components/empty-state.svelte';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import FilterChips from '$lib/components/scans/results/table/filter-chips.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import NoteFacet from '$lib/components/notes/note-facet.svelte';
	import NoteRow from '$lib/components/notes/note-row.svelte';
	import NoteSheet from '$lib/components/notes/note-sheet.svelte';
	import { canChangeNote } from '$lib/components/notes/subject';
	import {
		NOTE_FACETS,
		facetOptions,
		withPicks,
		type FacetOption,
		type NoteFacetParam
	} from '$lib/components/notes/facets';
	import { notesApi } from '$lib/api/notes';
	import { notes } from '$lib/stores/notes.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { routeLabels } from '$lib/config/routes';
	import { pageTitle } from '$lib/utilities/page-title';
	import { SEARCH_DEBOUNCE_MS } from '$lib/utilities/scan-status';
	import type { Note, NoteFacets, NoteFilter, NoteStatus } from '$lib/types/note';

	const PAGE_SIZES = [25, 50, 100];
	const PAGE_SIZE = 50;
	const NOTE_PARAM = 'note';

	let projectId = $derived(projectsStore.activeProject?.id ?? '');

	// ---------- url state ----------
	let sp = $derived(page.url.searchParams);
	let picks = $derived(
		Object.fromEntries(NOTE_FACETS.map((f) => [f.param, sp.getAll(f.param)])) as Record<
			NoteFacetParam,
			string[]
		>
	);
	let query = $derived(sp.get('q') ?? '');
	let pageIndex = $derived(Math.max(0, (Math.floor(Number(sp.get('page'))) || 1) - 1));
	let pageSize = $derived(
		PAGE_SIZES.includes(Number(sp.get('size'))) ? Number(sp.get('size')) : PAGE_SIZE
	);
	let noteId = $derived(sp.get(NOTE_PARAM));
	let filter = $derived<NoteFilter>({
		target_id: picks.target,
		dimension: picks.type,
		asset: picks.asset,
		scan: picks.scan,
		tag: picks.tag,
		author: picks.author,
		status: picks.status as NoteStatus[],
		triage: picks.triage,
		search: query || undefined
	});
	let filtered = $derived(!!query || NOTE_FACETS.some((f) => picks[f.param].length > 0));

	function update(mut: (s: URLSearchParams) => void, keepPage = false) {
		const url = new URL(page.url);
		mut(url.searchParams);
		if (!keepPage) url.searchParams.delete('page');
		void goto(url, { replaceState: true, noScroll: true, keepFocus: true });
	}

	function setList(param: string, values: string[]) {
		update((s) => {
			s.delete(param);
			for (const v of values) s.append(param, v);
		});
	}

	function setParam(param: string, value: string | null, keepPage = false) {
		update((s) => (value ? s.set(param, value) : s.delete(param)), keepPage);
	}

	function clearFilters() {
		draft = '';
		clearTimeout(searchTimer);
		update((s) => {
			s.delete('q');
			for (const f of NOTE_FACETS) s.delete(f.param);
		});
	}

	// ---------- search ----------
	let draft = $state('');
	let searchEl = $state<HTMLInputElement | null>(null);
	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		const applied = query;
		if (applied !== untrack(() => draft.trim())) draft = applied;
	});

	function onSearch(value: string) {
		draft = value;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => setParam('q', value.trim() || null), SEARCH_DEBOUNCE_MS);
	}

	// ---------- rows ----------
	let items = $state<Note[]>([]);
	let total = $state(0);
	let loading = $state(true);
	let loaded = $state(false);
	let failed = $state<string | null>(null);
	let listSeq = 0;
	const picked = new SvelteSet<string>();

	async function loadList(id: string, f: NoteFilter, index: number, size: number) {
		if (!id) return;
		const seq = ++listSeq;
		loading = true;
		try {
			const res = await notes.list(id, { ...f, page: index + 1, size });
			if (seq !== listSeq) return;
			const last = Math.max(1, Math.ceil(res.total / size));
			if (res.total > 0 && index + 1 > last) {
				setParam('page', String(last), true);
				return;
			}
			items = res.items;
			total = res.total;
			failed = null;
			loaded = true;
		} catch (e) {
			if (seq !== listSeq) return;
			failed = e instanceof Error ? e.message : 'Notes not loaded.';
			items = [];
			total = 0;
		} finally {
			if (seq === listSeq) loading = false;
		}
	}

	let listKey = $derived(JSON.stringify([projectId, filter, pageIndex, pageSize, notes.version]));
	$effect(() => {
		void listKey;
		untrack(() => loadList(projectId, filter, pageIndex, pageSize));
	});

	$effect(() => {
		const ids = new Set(items.map((n) => n.id));
		for (const id of picked) if (!ids.has(id)) picked.delete(id);
	});

	function toggleCheck(id: string) {
		if (picked.has(id)) picked.delete(id);
		else picked.add(id);
	}

	// ---------- facets ----------
	let facets = $state<NoteFacets | null>(null);
	let assetQuery = $state('');
	let facetSeq = 0;
	const known = new SvelteMap<string, FacetOption>();

	async function loadFacets(id: string, f: NoteFilter, assets: string) {
		if (!id) return;
		const seq = ++facetSeq;
		try {
			const res = await notes.facets(id, f, assets);
			if (seq !== facetSeq) return;
			facets = res;
			const options = facetOptions(res);
			for (const param of Object.keys(options) as NoteFacetParam[])
				for (const option of options[param]) known.set(`${param}\n${option.value}`, option);
		} catch {
			if (seq === facetSeq) facets = null;
		}
	}

	let facetKey = $derived(JSON.stringify([projectId, filter, assetQuery, notes.version]));
	$effect(() => {
		void facetKey;
		untrack(() => loadFacets(projectId, filter, assetQuery));
	});

	let options = $derived.by(() => {
		const base = facetOptions(facets);
		const out = {} as Record<NoteFacetParam, FacetOption[]>;
		for (const f of NOTE_FACETS)
			out[f.param] = withPicks(base[f.param], picks[f.param], (value) =>
				known.get(`${f.param}\n${value}`)
			);
		return out;
	});

	let chips = $derived(
		NOTE_FACETS.flatMap((f) =>
			picks[f.param].map((value) => {
				const label = options[f.param].find((o) => o.value === value)?.label ?? value;
				return {
					id: `${f.param}\n${value}`,
					label: f.param === 'tag' ? `#${label}` : `${f.title}: ${label}`,
					remove: () =>
						setList(
							f.param,
							picks[f.param].filter((v) => v !== value)
						)
				};
			})
		)
	);

	// ---------- project switch ----------
	let shownProject = '';
	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => {
			if (shownProject && shownProject !== id) {
				draft = '';
				known.clear();
				update((s) => {
					for (const param of ['q', NOTE_PARAM, ...NOTE_FACETS.map((f) => f.param)])
						s.delete(param);
				});
			}
			shownProject = id;
		});
	});

	// ---------- sheet ----------
	let sheetNote = $state<Note | null>(null);
	let sheetOpen = $derived(!!noteId && sheetNote?.id === noteId);

	$effect(() => {
		const id = noteId;
		const pid = projectId;
		if (!id || !pid) return;
		const hit = items.find((n) => n.id === id);
		if (hit) {
			sheetNote = hit;
			return;
		}
		if (untrack(() => sheetNote?.id) === id) return;
		notes
			.get(pid, id)
			.then((found) => {
				if (noteId === id) sheetNote = found;
			})
			.catch(() => {
				if (noteId !== id) return;
				toast.error('Note not found');
				setParam(NOTE_PARAM, null, true);
			});
	});

	function openNote(note: Note) {
		sheetNote = note;
		setParam(NOTE_PARAM, note.id, true);
	}

	// facets with nothing to pick are hidden; past the first few, small screens fold them away
	const INLINE_FACETS = 3;
	let shownFacets = $derived(
		NOTE_FACETS.filter(
			(f) =>
				options[f.param].length > 0 ||
				picks[f.param].length > 0 ||
				(f.param === 'asset' && !!assetQuery)
		)
	);
	let moreFacets = $derived(shownFacets.slice(INLINE_FACETS));
	let moreSelected = $derived(moreFacets.reduce((n, f) => n + picks[f.param].length, 0));

	// ---------- keyboard ----------
	function onKey(e: KeyboardEvent) {
		if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
		const el = e.target as HTMLElement | null;
		if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return;
		if (document.querySelector('[role=dialog],[role=menu]')) return;
		e.preventDefault();
		searchEl?.focus();
	}
</script>

{#snippet facet(f: (typeof NOTE_FACETS)[number])}
	<NoteFacet
		title={f.title}
		options={options[f.param]}
		selected={picks[f.param]}
		onChange={(next) => setList(f.param, next)}
		onSearch={f.param === 'asset' ? (q) => (assetQuery = q) : undefined}
	/>
{/snippet}

<svelte:head><title>{pageTitle(routeLabels.notes)}</title></svelte:head>
<svelte:window onkeydown={onKey} />

<div class="flex flex-col gap-6">
	<h1 class="text-2xl font-semibold tracking-tight">Notes</h1>

	<Card.Root class="gap-0 overflow-hidden py-0">
		{#if filtered || total > 0 || !loaded}
			<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
				<InputGroup.Root class="w-auto min-w-[240px] flex-1">
					<InputGroup.Addon>
						<Search />
					</InputGroup.Addon>
					<InputGroup.Input
						bind:ref={searchEl}
						placeholder="Search notes"
						value={draft}
						oninput={(e) => onSearch(e.currentTarget.value)}
						onkeydown={(e) => {
							if (e.key === 'Enter') {
								clearTimeout(searchTimer);
								setParam('q', draft.trim() || null);
							}
							if (e.key === 'Escape') e.currentTarget.blur();
						}}
						aria-label="Search notes"
					/>
					<InputGroup.Addon align="inline-end">
						{#if draft}
							<InputGroup.Button
								size="icon-xs"
								aria-label="Clear search"
								onclick={() => onSearch('')}
							>
								<X />
							</InputGroup.Button>
						{:else}
							<Kbd class="hidden sm:inline-flex">/</Kbd>
						{/if}
					</InputGroup.Addon>
				</InputGroup.Root>
				{#each shownFacets as f, i (f.param)}
					<span class={i >= INLINE_FACETS ? 'contents max-sm:hidden' : 'contents'}>
						{@render facet(f)}
					</span>
				{/each}
				{#if moreFacets.length}
					<Popover.Root>
						<Popover.Trigger>
							{#snippet child({ props })}
								<Button
									{...props}
									variant="outline"
									class="sm:hidden {moreSelected ? 'border-primary/50 bg-primary/5' : ''}"
								>
									<ListFilter />
									More filters
									{#if moreSelected}
										<Badge variant="secondary" class="h-5 px-1.5 text-xs">{moreSelected}</Badge>
									{/if}
								</Button>
							{/snippet}
						</Popover.Trigger>
						<Popover.Content
							align="end"
							class="flex w-auto max-w-[calc(100vw-2rem)] flex-wrap gap-2 p-2"
						>
							{#each moreFacets as f (f.param)}
								{@render facet(f)}
							{/each}
						</Popover.Content>
					</Popover.Root>
				{/if}
			</div>

			<FilterChips {chips} onRemove={(chip) => chip.remove()} onClear={clearFilters} />
		{/if}

		{#if loading && !loaded}
			<RowSkeleton rows={6} avatar={null} trailing="h-3.5 w-20" />
		{:else if failed}
			<EmptyState
				icon={TriangleAlert}
				title="Notes not loaded"
				description={failed}
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" onclick={() => notes.touch()}>Retry</Button>
			</EmptyState>
		{:else if items.length === 0}
			<EmptyState
				icon={StickyNote}
				title={filtered ? 'No notes match' : 'No notes'}
				class="rounded-none border-0 bg-transparent py-16"
			>
				{#if filtered}
					<Button variant="outline" size="sm" onclick={clearFilters}>Clear filters</Button>
				{/if}
			</EmptyState>
		{:else}
			<div class={loading ? 'opacity-60' : ''}>
				{#each items as note (note.id)}
					<NoteRow
						{note}
						checked={picked.has(note.id)}
						selectable={canChangeNote(note, auth.user)}
						active={sheetOpen && note.id === noteId}
						onCheck={toggleCheck}
						onOpen={openNote}
					/>
				{/each}
			</div>
			<ResultsPagination
				{total}
				page={pageIndex}
				{pageSize}
				noun="note"
				sizes={PAGE_SIZES}
				onPage={(p) => setParam('page', p > 0 ? String(p + 1) : null, true)}
				onPageSize={(size) => setParam('size', size === PAGE_SIZE ? null : String(size))}
			/>
		{/if}
	</Card.Root>
</div>

<NoteSheet
	note={sheetNote}
	open={sheetOpen}
	onOpenChange={(open) => {
		if (!open) setParam(NOTE_PARAM, null, true);
	}}
/>

<SelectionDeleteBar
	ids={[...picked]}
	noun="note"
	remove={(id) => notesApi.remove(projectId, id)}
	onDone={() => {
		picked.clear();
		notes.touch();
	}}
	onClear={() => picked.clear()}
/>
