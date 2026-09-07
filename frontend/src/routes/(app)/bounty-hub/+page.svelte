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

	const projectId = $derived(projectsStore.activeProject?.id);
	const filterKey = $derived(JSON.stringify(filters));

	async function loadStatus() {
		try {
			status = await bountyProgramsApi.status();
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Could not read the Bounty Hub status');
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
			toast.error(error instanceof Error ? error.message : 'Could not load programs');
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
		}
	});

	// a deep link opens any program, not only one on the page being shown
	let deepLinked = $state<string | null>(null);

	$effect(() => {
		const handle = page.url.searchParams.get('program');
		const platform = page.url.searchParams.get('platform') ?? undefined;
		if (!handle || sheetOpen || deepLinked === handle) return;
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
		if (!value) deepLinked = null;
		if (!value && page.url.searchParams.has('program')) {
			void goto(ROUTES.bountyHub(), { replaceState: true, noScroll: true, keepFocus: true });
		}
	}

	async function sync() {
		syncing = true;
		try {
			await Promise.all([bountyProgramsApi.sync(), bountyProgramsApi.syncFeed()]);
			toast.success('Refreshing every platform. This runs in the background.');
		} catch (error) {
			toast.error(error instanceof Error ? error.message : 'Could not start the refresh');
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
					Browse the bug bounty programs your HackerOne account can see, and add their scope as
					targets.
				{/if}
			</p>
		</div>

		{#if status?.configured}
			<LoadingButton loading={syncing} variant="outline" size="sm" onclick={sync}>
				<RefreshCwIcon class="mr-2 size-3.5" />
				Refresh all platforms
			</LoadingButton>
		{/if}
	</div>

	{#if status && !status.configured}
		<Card.Root>
			<EmptyState
				icon={KeyRoundIcon}
				title="Connect your HackerOne account"
				description="Bounty Hub reads programs and their structured scope with your HackerOne API username and token. Public and private programs your account can see will appear here."
				class="p-10"
			>
				<Button href={ROUTES.settings('api-keys')} size="sm">Add HackerOne credentials</Button>
			</EmptyState>
		</Card.Root>
	{:else}
		<CountTabs
			tabs={[
				{ key: 'programs', label: 'Programs' },
				{ key: 'updates', label: 'Updates' }
			]}
			counts={{ programs: total, updates: status?.unseen_events ?? 0 }}
			value={tab}
			onChange={(k) => (tab = k as BountyHubTab)}
		/>

		{#if tab === 'updates'}
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
							? 'No programs yet'
							: 'No programs match these filters'}
						description={total === 0 && status?.programs === 0
							? 'Refresh from HackerOne to pull the programs your account can see.'
							: 'Try clearing a filter.'}
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
/>
