<script lang="ts">
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import TargetIcon from '@lucide/svelte/icons/target';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { Spinner } from '$lib/components/ui/spinner';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import FilterBar from '$lib/components/bounty-hub/filter-bar.svelte';
	import UpdatesFeed from '$lib/components/bounty-hub/updates-feed.svelte';
	import ProgramRow from '$lib/components/bounty-hub/program-row.svelte';
	import ProgramSheet from '$lib/components/bounty-hub/program-sheet.svelte';
	import WatchingTab from '$lib/components/bounty-hub/watching-tab.svelte';
	import WatchSheet from '$lib/components/bounty-hub/watch-sheet.svelte';
	import { watchesApi } from '$lib/api/watches';
	import { watchesStore } from '$lib/stores/watches.svelte';
	import type { StreamStatus, Watch, WatchHostFilter } from '$lib/types/watch';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import { PROGRAM_PAGE_SIZE, SYNC_INTERVAL_LABELS } from '$lib/config/bounty-programs';
	import { BOUNTY_HUB_TABS, ROUTES, type BountyHubTab } from '$lib/config/routes';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import type {
		BountyProgram,
		BountyProgramFilters,
		BountyStatus
	} from '$lib/types/bounty-program';

	let status = $state<BountyStatus | null>(null);
	let programs = $state<BountyProgram[]>([]);
	let total = $state(0);
	let pageIndex = $state(0);
	let pageSize = $state(PROGRAM_PAGE_SIZE);
	let loading = $state(true);
	let syncing = $state(false);
	let selected = $state<BountyProgram | null>(null);
	let sheetOpen = $state(false);
	let filters = $state<BountyProgramFilters>({ sort: 'age' });
	let tab = $state<BountyHubTab>('programs');
	let tabChosen = $state(false);
	let watchOpen = $state(false);
	let selectedWatch = $state<Watch | null>(null);
	let watchFilter = $state<WatchHostFilter>('all');
	let watchTab = $state<'hosts' | 'activity'>('hosts');
	let deepLinkedWatch = $state<string | null>(null);
	let stream = $state<StreamStatus | null>(null);

	const projectId = $derived(projectsStore.activeProject?.id);
	const filterKey = $derived(JSON.stringify(filters));

	async function loadStatus() {
		try {
			status = await bountyProgramsApi.status();
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Bounty Hub status not loaded');
		}
	}

	async function loadPrograms(
		f: BountyProgramFilters,
		index: number,
		size: number,
		project: string | undefined
	) {
		loading = true;
		try {
			const result = await bountyProgramsApi.list(f, index + 1, size, project);
			programs = result.items;
			total = result.total;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Programs not loaded');
			programs = [];
			total = 0;
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		void loadStatus();
	});

	$effect(() => {
		void filterKey;
		void loadPrograms(filters, pageIndex, pageSize, projectId);
	});

	$effect(() => {
		const requested = page.url.searchParams.get('tab');
		if (requested && (BOUNTY_HUB_TABS as readonly string[]).includes(requested)) {
			tab = requested as BountyHubTab;
			tabChosen = true;
		}
	});

	$effect(() => {
		if (!projectId) return;
		if (watchesStore.fetchedProjectId !== projectId) {
			void watchesStore.fetch(projectId).then(() => {
				if (!tabChosen && watchesStore.watches.length > 0) tab = 'watching';
			});
		}
		void watchesApi
			.stream()
			.then((s) => (stream = s))
			.catch(() => (stream = null));
	});

	$effect(() => {
		const id = page.url.searchParams.get('watch');
		if (!id) {
			deepLinkedWatch = null;
			return;
		}
		if (watchOpen || deepLinkedWatch === id) return;
		const match = watchesStore.watches.find((w) => w.id === id);
		if (match || (projectId && !watchesStore.isLoading)) deepLinkedWatch = id;
		if (match) {
			openWatch(match);
			return;
		}
		if (!projectId || watchesStore.isLoading) return;
		void watchesApi
			.get(id, projectId)
			.then((w) => openWatch(w))
			.catch(() => toast.error('Watch not found'));
	});

	function openWatch(
		watch: Watch,
		filter: WatchHostFilter = 'all',
		sheetTab: 'hosts' | 'activity' = 'hosts'
	) {
		selectedWatch = watch;
		watchFilter = filter;
		watchTab = sheetTab;
		watchOpen = true;
		tab = 'watching';
	}

	function onWatchOpen(value: boolean) {
		watchOpen = value;
		if (!value && page.url.searchParams.has('watch')) {
			void goto(ROUTES.bountyHubTab('watching'), {
				replaceState: true,
				noScroll: true,
				keepFocus: true
			});
		}
	}

	function onWatched(watch: Watch) {
		watchesStore.upsert(watch);
		sheetOpen = false;
		void goto(ROUTES.bountyWatch(watch.id), { noScroll: true, keepFocus: true });
	}

	let deepLinked = $state<string | null>(null);

	$effect(() => {
		const handle = page.url.searchParams.get('program');
		const platform = page.url.searchParams.get('platform') ?? undefined;
		// the sheet would immediately reopen it
		if (!handle) {
			deepLinked = null;
			return;
		}
		if (sheetOpen || deepLinked === handle) return;
		deepLinked = handle;
		const match = programs.find(
			(p) => p.handle === handle && (!platform || p.platform === platform)
		);
		if (match) {
			open(match);
			return;
		}
		void bountyProgramsApi
			.detail(handle, projectId, null, platform)
			.then((program) => open(program))
			.catch(() => toast.error(`No program found for @${handle}`));
	});

	function openProgram(handle: string, platform: string) {
		tab = 'programs';
		void goto(ROUTES.bountyHub(handle, platform), { noScroll: true, keepFocus: true });
	}

	function onFilters(next: BountyProgramFilters) {
		filters = next;
		pageIndex = 0;
	}

	function open(program: BountyProgram) {
		selected = program;
		sheetOpen = true;
	}

	function onSheetOpen(value: boolean) {
		sheetOpen = value;
		if (!value && page.url.searchParams.has('program')) {
			void goto(ROUTES.bountyHub(), { replaceState: true, noScroll: true, keepFocus: true });
		}
	}

	async function sync() {
		syncing = true;
		try {
			await Promise.all([
				status?.configured ? bountyProgramsApi.sync() : Promise.resolve(),
				bountyProgramsApi.syncFeed()
			]);
			toast.success('Refresh started');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Refresh not started');
		} finally {
			syncing = false;
		}
	}
</script>

<svelte:head><title>Bounty Hub · reNgine</title></svelte:head>

<div class="flex flex-col gap-4 p-4">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="flex flex-col gap-1">
			<h1 class="text-xl font-semibold">Bounty Hub</h1>
			<p class="text-sm text-muted-foreground">
				{#if status}
					{status.programs.toLocaleString()} programs across {status.platforms.filter(
						(p) => p.programs > 0
					).length} platforms
					{#if status.private_programs > 0}
						· {status.private_programs} private
					{/if}
					{#if status.last_synced_at}
						· synced {relativeTime(status.last_synced_at)}
					{/if}
					·
					<a href={ROUTES.settings('bounty-hub')} class="hover:underline">
						{SYNC_INTERVAL_LABELS[status.sync_interval] ?? status.sync_interval}
					</a>
				{:else}
					Bug bounty programs and their scope
				{/if}
			</p>
		</div>

		<LoadingButton loading={syncing} variant="outline" size="sm" onclick={sync}>
			<RefreshCwIcon class="mr-2 size-3.5" />
			Refresh all platforms
		</LoadingButton>
	</div>

	{#if status && !status.configured}
		<Card.Root class="border-dashed">
			<div class="flex flex-wrap items-center justify-between gap-3 p-4">
				<div class="flex min-w-0 items-start gap-3">
					<KeyRoundIcon class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
					<div class="flex min-w-0 flex-col gap-0.5">
						<span class="text-sm font-medium">HackerOne is not connected</span>
						<span class="text-xs text-muted-foreground">
							A HackerOne API token adds its public and private programs.
						</span>
					</div>
				</div>
				<Button href={ROUTES.settings('api-keys')} size="sm" variant="outline">Add API key</Button>
			</div>
		</Card.Root>
	{/if}

	{#if status || watchesStore.watches.length > 0}
		<CountTabs
			tabs={[
				{ key: 'watching', label: 'Watching' },
				{ key: 'programs', label: 'Programs' },
				{ key: 'updates', label: 'Updates' }
			]}
			counts={{
				watching: watchesStore.watches.length,
				programs: total,
				updates: status?.unseen_events ?? 0
			}}
			value={tab}
			onChange={(k) => {
				tab = k as BountyHubTab;
				tabChosen = true;
			}}
		/>

		{#if tab === 'watching'}
			<WatchingTab
				watches={watchesStore.watches}
				loading={watchesStore.isLoading}
				{stream}
				onOpen={openWatch}
				onBrowsePrograms={() => {
					tab = 'programs';
					tabChosen = true;
				}}
			/>
		{:else if tab === 'updates'}
			<UpdatesFeed onOpenProgram={openProgram} />
		{:else}
			<FilterBar {filters} platforms={status?.platforms ?? []} onChange={onFilters} />

			<Card.Root class="gap-0 overflow-hidden py-0">
				{#if loading}
					<div class="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground">
						<Spinner class="size-4" />
						Loading programs
					</div>
				{:else if programs.length === 0}
					<EmptyState
						icon={TargetIcon}
						title={total === 0 && status?.programs === 0
							? 'No programs'
							: 'No programs match these filters'}
						description={total === 0 && status?.programs === 0
							? 'Refresh all platforms to load programs.'
							: 'Clear a filter.'}
						class="p-12"
					/>
				{:else}
					{#each programs as program (program.id)}
						<ProgramRow {program} onOpen={open} />
					{/each}
				{/if}
			</Card.Root>

			{#if total > pageSize}
				<ResultsPagination
					page={pageIndex}
					{pageSize}
					{total}
					noun="program"
					onPage={(p) => (pageIndex = p)}
					onPageSize={(s) => {
						pageSize = s;
						pageIndex = 0;
					}}
				/>
			{/if}
		{/if}
	{/if}
</div>

<ProgramSheet
	program={selected}
	{projectId}
	open={sheetOpen}
	onOpenChange={onSheetOpen}
	onImported={() => loadPrograms(filters, pageIndex, pageSize, projectId)}
	onWatch={onWatched}
	onOpenWatch={(id) => {
		sheetOpen = false;
		void goto(ROUTES.bountyWatch(id), { noScroll: true, keepFocus: true });
	}}
/>

{#if projectId}
	<WatchSheet
		watch={selectedWatch}
		{projectId}
		open={watchOpen}
		initialFilter={watchFilter}
		initialTab={watchTab}
		onOpenChange={onWatchOpen}
		onChanged={(w) => {
			if (w) selectedWatch = w;
			void loadPrograms(filters, pageIndex, pageSize, projectId);
		}}
	/>
{/if}
