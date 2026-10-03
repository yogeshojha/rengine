<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { untrack } from 'svelte';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import SettingsIcon from '@lucide/svelte/icons/settings';
	import NewspaperIcon from '@lucide/svelte/icons/newspaper';
	import TargetIcon from '@lucide/svelte/icons/target';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { toast } from 'svelte-sonner';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/card';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import { Button } from '$lib/components/ui/button';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import FilterBar from '$lib/components/bounty-hub/filter-bar.svelte';
	import ConnectAlert from '$lib/components/bounty-hub/connect-alert.svelte';
	import UpdatesFeed from '$lib/components/bounty-hub/updates-feed.svelte';
	import ProgramRow from '$lib/components/bounty-hub/program-row.svelte';
	import ProgramSheet from '$lib/components/bounty-hub/program-sheet.svelte';
	import WatchingTab from '$lib/components/bounty-hub/watching-tab.svelte';
	import WatchSheet from '$lib/components/bounty-hub/watch-sheet.svelte';
	import SettingsSheet from '$lib/components/bounty-hub/settings-sheet.svelte';
	import { watchesApi } from '$lib/api/watches';
	import { watchesStore } from '$lib/stores/watches.svelte';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { WatchHostFilter, type StreamStatus, type Watch } from '$lib/types/watch';
	import { bountyProgramsApi } from '$lib/api/bounty-programs';
	import {
		DEFAULT_PROGRAM_SORT,
		PROGRAM_PAGE_SIZE,
		REFRESH_POLLS,
		REFRESH_POLL_MS,
		SYNC_INTERVAL_LABELS
	} from '$lib/config/bounty-programs';
	import {
		BOUNTY_HUB_TABS,
		BOUNTY_SETTINGS_PANEL,
		PANEL_PARAM,
		ROUTES,
		routeLabels,
		type BountyHubTab
	} from '$lib/config/routes';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import type {
		BountyProgram,
		BountyProgramFilters,
		BountyStatus
	} from '$lib/types/bounty-program';

	let status = $state<BountyStatus | null>(null);
	let statusError = $state<string | null>(null);
	let programs = $state<BountyProgram[]>([]);
	let programsError = $state<string | null>(null);
	let total = $state(0);
	let pageIndex = $state(0);
	let pageSize = $state(PROGRAM_PAGE_SIZE);
	let loading = $state(true);
	let programsSeq = 0;
	let syncing = $state(false);
	let selected = $state<BountyProgram | null>(null);
	let sheetOpen = $state(false);
	let filters = $state<BountyProgramFilters>({ sort: DEFAULT_PROGRAM_SORT });
	let tab = $state<BountyHubTab>('programs');
	let tabChosen = $state(false);
	let watchOpen = $state(false);
	let selectedWatch = $state<Watch | null>(null);
	let watchFilter = $state<WatchHostFilter>(WatchHostFilter.All);
	let watchTab = $state<'hosts' | 'activity'>('hosts');
	let deepLinkedWatch = $state<string | null>(null);
	let stream = $state<StreamStatus | null>(null);
	let settingsOpen = $state(page.url.searchParams.get(PANEL_PARAM) === BOUNTY_SETTINGS_PANEL);

	$effect(() => {
		if (page.url.searchParams.get(PANEL_PARAM) === BOUNTY_SETTINGS_PANEL)
			untrack(() => (settingsOpen = true));
	});

	$effect(() => {
		if (settingsOpen) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (params.get(PANEL_PARAM) !== BOUNTY_SETTINGS_PANEL) return;
		params.delete(PANEL_PARAM);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

	const projectId = $derived(projectsStore.activeProject?.id);
	const filterKey = $derived(JSON.stringify(filters));

	async function loadStatus() {
		try {
			status = await bountyProgramsApi.status();
			statusError = null;
		} catch (error) {
			statusError = error instanceof Error ? error.message : 'Bounty Hub status not loaded';
			toast.error(statusError);
		}
	}

	async function loadPrograms(
		f: BountyProgramFilters,
		index: number,
		size: number,
		project: string | undefined
	) {
		const seq = ++programsSeq;
		loading = true;
		try {
			const result = await bountyProgramsApi.list(f, index + 1, size, project);
			if (seq !== programsSeq) return;
			programs = result.items;
			total = result.total;
			programsError = null;
		} catch (error) {
			if (seq !== programsSeq) return;
			programsError = error instanceof Error ? error.message : 'Programs not loaded';
			toast.error(programsError);
			programs = [];
			total = 0;
		} finally {
			if (seq === programsSeq) loading = false;
		}
	}

	$effect(() => {
		void loadStatus();
	});

	$effect(() => {
		void filterKey;
		if (!projectsStore.hasFetched) return;
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
		untrack(() => bountyVocabulary.load());
	});

	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => {
			if (watchesStore.fetchedProjectId !== id) {
				void watchesStore.fetch(id).then(() => {
					if (!tabChosen && watchesStore.watches.length > 0) tab = 'watching';
				});
			}
			void watchesApi
				.stream()
				.then((st) => (stream = st))
				.catch(() => (stream = null));
		});
	});

	$effect(() => {
		const id = page.url.searchParams.get('watch');
		if (!id) {
			untrack(() => {
				if (deepLinkedWatch) watchOpen = false;
				deepLinkedWatch = null;
			});
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
			.catch(() => {
				toast.error('Watch not found');
				void goto(ROUTES.bountyHubTab('watching'), {
					replaceState: true,
					noScroll: true,
					keepFocus: true
				});
			});
	});

	function openWatch(
		watch: Watch,
		filter: WatchHostFilter = WatchHostFilter.All,
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
		if (!handle) {
			untrack(() => {
				if (deepLinked) sheetOpen = false;
				deepLinked = null;
			});
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
			.detail(handle, projectId, platform)
			.then((program) => open(program))
			.catch(() => toast.error(`Program @${handle} not found`));
	});

	function openProgram(handle: string, platform: string) {
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

	const anyConnected = $derived((status?.platforms ?? []).some((p) => p.configured));

	async function settled(before: string | null): Promise<boolean> {
		for (let i = 0; i < REFRESH_POLLS; i++) {
			await new Promise((r) => setTimeout(r, REFRESH_POLL_MS));
			const next = await bountyProgramsApi.status().catch(() => null);
			if (!next) continue;
			status = next;
			if (next.last_synced_at !== before) return true;
		}
		return false;
	}

	async function sync() {
		syncing = true;
		const before = status?.last_synced_at ?? null;
		try {
			await Promise.all([
				anyConnected ? bountyProgramsApi.sync() : Promise.resolve(),
				bountyProgramsApi.syncFeed()
			]);
			const done = await settled(before);
			await loadPrograms(filters, pageIndex, pageSize, projectId);
			toast.success(done ? 'Programs refreshed' : 'Refresh running');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Refresh not started');
		} finally {
			syncing = false;
		}
	}
</script>

<svelte:head><title>{pageTitle(routeLabels['bounty-hub'])}</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="min-w-0">
			<h1 class="text-2xl font-semibold tracking-tight">{routeLabels['bounty-hub']}</h1>
			<p class="mt-1 text-sm text-muted-foreground">
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
					<button
						type="button"
						class="transition-colors hover:text-foreground"
						onclick={() => (settingsOpen = true)}
					>
						{SYNC_INTERVAL_LABELS[status.sync_interval] ?? status.sync_interval}
					</button>
				{:else}
					Bug bounty programs and their scope
				{/if}
			</p>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<Button variant="outline" size="sm" href={ROUTES.whatsNew()}>
				<NewspaperIcon class="size-4" />
				What's new
			</Button>
			<LoadingButton
				loading={syncing}
				loadingLabel="Refreshing"
				variant="outline"
				size="sm"
				onclick={sync}
			>
				<RefreshCwIcon class="size-4" />
				Refresh all platforms
			</LoadingButton>
			<Button variant="outline" size="sm" onclick={() => (settingsOpen = true)}>
				<SettingsIcon class="size-4" />
				Settings
			</Button>
		</div>
	</div>

	<ConnectAlert platforms={status?.platforms ?? []} />

	{#if status || watchesStore.watches.length > 0}
		<div class="flex flex-col gap-4">
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
					error={watchesStore.error}
					{stream}
					onOpen={openWatch}
					onRetry={() => {
						if (projectId) void watchesStore.fetch(projectId);
					}}
					onBrowsePrograms={() => {
						tab = 'programs';
						tabChosen = true;
					}}
				/>
			{:else if tab === 'updates'}
				<UpdatesFeed onOpenProgram={openProgram} />
			{:else}
				<Card.Root class="gap-0 overflow-hidden py-0">
					<FilterBar
						{filters}
						platforms={status?.platforms ?? []}
						sourceCounts={status?.source_counts ?? {}}
						onChange={onFilters}
					/>

					{#if loading}
						<RowSkeleton />
					{:else if programsError}
						<EmptyState
							icon={TriangleAlertIcon}
							title="Programs not loaded"
							description={programsError}
							compact
							class="rounded-none border-0 bg-transparent py-16"
						>
							<Button
								variant="outline"
								size="sm"
								onclick={() => loadPrograms(filters, pageIndex, pageSize, projectId)}
							>
								Retry
							</Button>
						</EmptyState>
					{:else if programs.length === 0}
						<EmptyState
							icon={TargetIcon}
							title={total === 0 && status?.programs === 0
								? 'No programs'
								: 'No programs match these filters'}
							compact
							class="rounded-none border-0 bg-transparent py-16"
						/>
					{:else}
						{#each programs as program (program.id)}
							<ProgramRow {program} onOpen={open} />
						{/each}
					{/if}

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
				</Card.Root>
			{/if}
		</div>
	{:else if statusError}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<EmptyState
				icon={TriangleAlertIcon}
				title="{routeLabels['bounty-hub']} not loaded"
				description={statusError}
				compact
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" onclick={() => loadStatus()}>Retry</Button>
			</EmptyState>
		</Card.Root>
	{:else}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<RowSkeleton />
		</Card.Root>
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

<SettingsSheet bind:open={settingsOpen} onSaved={() => void loadStatus()} />
