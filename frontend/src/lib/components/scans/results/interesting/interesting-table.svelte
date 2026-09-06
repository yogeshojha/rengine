<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import Sparkle from '@lucide/svelte/icons/sparkle';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Eye from '@lucide/svelte/icons/eye';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import { interestApi } from '$lib/api/interest';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { INTEREST_SORTS, kindIcon, sourceIcon } from '$lib/config/interest';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import type { InterestPage, InterestRow, RuleSuggestion } from '$lib/types/interest';
	import InterestRowItem from './interest-row.svelte';
	import InterestDetailSheet from './interest-detail-sheet.svelte';
	import SuggestionRow from './suggestion-row.svelte';

	interface Props {
		scanId: string;
		targetId: string;
		projectId: string;
		active: boolean;
		onTab: (tab: string, filter?: string) => void;
		onTotal?: (total: number) => void;
	}

	let { scanId, targetId, projectId, active, onTab, onTotal }: Props = $props();

	const PAGE_SIZE = 25;
	const ALL = 'all';
	const STALE_RETRY_MS = 5000;

	let data = $state<InterestPage | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let band = $state(ALL);
	let q = $state('');
	let sources = $state<string[]>([]);
	let kinds = $state<string[]>([]);
	let sort = $state<string>('score');
	let page = $state(1);
	let judging = $state(false);
	let retry: ReturnType<typeof setTimeout> | null = null;
	let suggestions = $state<RuleSuggestion[]>([]);
	let askedFor = '';
	let selected = $state<InterestRow | null>(null);
	let loaded = false;

	let summary = $derived(data?.summary ?? null);
	let bandTabs = $derived([
		{ key: ALL, label: 'All' },
		...(interestCatalog.catalog?.bands ?? []).map((b) => ({ key: b.key, label: b.label }))
	]);
	let bandCounts = $derived({
		[ALL]: summary ? Object.values(summary.bands).reduce((a, b) => a + b, 0) : 0,
		...(summary?.bands ?? {})
	});
	let activeKinds = $derived(
		(interestCatalog.catalog?.kinds ?? []).filter((k) => (summary?.kinds?.[k.key] ?? 0) > 0)
	);
	let activeSources = $derived(
		(interestCatalog.catalog?.sources ?? []).filter((s) => (summary?.sources?.[s.key] ?? 0) > 0)
	);
	let filtered = $derived(q.trim() !== '' || sources.length > 0 || kinds.length > 0);

	$effect(() => {
		void interestCatalog.load();
	});

	let signature = $derived(
		JSON.stringify({ scanId, band, q: q.trim(), sources, kinds, sort, page })
	);

	// the first load always runs so the tab can decide whether it has earned its place
	$effect(() => {
		void signature;
		if (loaded && !active) return;
		loaded = true;
		void run();
	});

	// a suggestion costs a model call, so it is asked for once, and only where AI judged something
	$effect(() => {
		const s = summary;
		if (!active || !s?.ai_enabled || !s.judged_hosts || askedFor === scanId) return;
		askedFor = scanId;
		void loadSuggestions();
	});

	async function loadSuggestions(): Promise<void> {
		try {
			suggestions = await interestApi.suggestions(scanId);
		} catch {
			suggestions = [];
		}
	}

	async function run(): Promise<void> {
		loading = true;
		try {
			const result = await interestApi.scan(scanId, {
				q: q.trim() || null,
				bands: band === ALL ? [] : [band],
				sources,
				kinds,
				sort,
				order: sort === 'host' ? 'asc' : 'desc',
				limit: PAGE_SIZE,
				offset: (page - 1) * PAGE_SIZE
			});
			data = result;
			error = null;
			onTotal?.(result.summary.total);
			// a scan the rules have not been run against refreshes itself once the worker catches up
			if (result.summary.stale && retry === null) {
				retry = setTimeout(() => {
					retry = null;
					void run();
				}, STALE_RETRY_MS);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load what is worth a look';
		} finally {
			loading = false;
		}
	}

	function toggle(list: string[], value: string): string[] {
		return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
	}

	async function judge(): Promise<void> {
		judging = true;
		try {
			await interestApi.judge(scanId);
			toast.success('Judging this scan. Refresh to see the result.');
		} catch {
			toast.error('Could not start judging');
		} finally {
			judging = false;
		}
	}

	async function dismiss(row: InterestRow): Promise<void> {
		try {
			await interestApi.dismiss({ host: row.host, target_id: targetId });
			toast.success(`${row.host} will stay out of this list`);
			await run();
		} catch {
			toast.error(`Could not dismiss ${row.host}`);
		}
	}

	function pickKind(kind: string): void {
		kinds = toggle(kinds, kind);
		page = 1;
	}

	$effect(() => () => {
		if (retry !== null) clearTimeout(retry);
	});

	function openInAssets(row: InterestRow): void {
		onTab('web-assets', `host="${row.host}"`);
	}
</script>

<div class="flex flex-col gap-4">
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
			<div class="flex min-w-0 flex-col gap-0.5">
				<h2 class="text-base leading-6 font-semibold">Worth a look</h2>
				<p class="text-xs text-muted-foreground">
					{#if summary && summary.total > 0}
						{summary.total.toLocaleString()}
						{summary.total === 1 ? 'asset' : 'assets'} flagged
						{#each activeSources as s, i (s.key)}{i === 0 ? ' · ' : ' · '}{(
								summary.sources[s.key] ?? 0
							).toLocaleString()}
							{s.key === 'ai' ? 'judged by AI' : `from ${s.label.toLowerCase()}`}{/each}
					{:else}
						Rules, correlations and AI judgement, in one ranked list
					{/if}
				</p>
			</div>
			<div class="flex shrink-0 items-center gap-2">
				{#if summary?.ai_enabled}
					<LoadingButton
						variant="outline"
						size="sm"
						loading={judging}
						loadingLabel="Starting"
						onclick={judge}
					>
						<Sparkle class="size-3.5" />
						{summary.judged_at ? 'Judge again' : 'Judge with AI'}
					</LoadingButton>
				{:else if summary?.ai_available}
					<Hint text="Enable Asset judgement on the AI page to include AI signals">
						{#snippet child(props)}
							<Button {...props} variant="outline" size="sm" href={ROUTES.ai('features')}>
								<Sparkle class="size-3.5" />
								Add AI judgement
							</Button>
						{/snippet}
					</Hint>
				{/if}
				<Hint text="Rules, keywords and notifications">
					{#snippet child(props)}
						<Button {...props} variant="ghost" size="sm" href={ROUTES.interest('rules')}>
							Manage rules
						</Button>
					{/snippet}
				</Hint>
				<Button variant="ghost" size="icon" class="size-8" onclick={run} aria-label="Refresh">
					<RefreshCw class="size-3.5 {loading ? 'animate-spin' : ''}" />
				</Button>
			</div>
		</div>

		<div class="border-b px-4">
			<CountTabs
				tabs={bandTabs}
				value={band}
				counts={bandCounts}
				onChange={(key) => {
					band = key;
					page = 1;
				}}
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2 border-b px-4 py-2.5">
			<div class="relative min-w-56 flex-1">
				<Search
					class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
				/>
				<Input
					bind:value={q}
					placeholder="Filter by hostname"
					class="h-8 pl-8 text-sm"
					oninput={() => (page = 1)}
				/>
			</div>

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm" class="h-8">
							<SlidersHorizontal class="size-3.5" />
							Reason
							{#if kinds.length}<span class="tabular-nums">{kinds.length}</span>{/if}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="max-h-none w-64 overflow-visible">
					<ScrollArea.Root
						class="[&_[data-slot=scroll-area-viewport]]:max-h-72"
						orientation="vertical"
					>
						{#each activeKinds as k (k.key)}
							{@const Icon = kindIcon(k.key)}
							<DropdownMenu.CheckboxItem
								checked={kinds.includes(k.key)}
								onCheckedChange={() => pickKind(k.key)}
							>
								<Icon class="size-3.5 text-muted-foreground" />
								<span class="flex-1 truncate">{k.label}</span>
								<span class="text-xs tabular-nums text-muted-foreground"
									>{summary?.kinds?.[k.key] ?? 0}</span
								>
							</DropdownMenu.CheckboxItem>
						{/each}
					</ScrollArea.Root>
				</DropdownMenu.Content>
			</DropdownMenu.Root>

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm" class="h-8">
							Flagged by
							{#if sources.length}<span class="tabular-nums">{sources.length}</span>{/if}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="w-56">
					{#each activeSources as s (s.key)}
						{@const Icon = sourceIcon(s.key)}
						<DropdownMenu.CheckboxItem
							checked={sources.includes(s.key)}
							onCheckedChange={() => {
								sources = toggle(sources, s.key);
								page = 1;
							}}
						>
							<Icon class="size-3.5 text-muted-foreground" />
							<span class="flex-1 truncate">{s.label}</span>
							<span class="text-xs tabular-nums text-muted-foreground"
								>{summary?.sources?.[s.key] ?? 0}</span
							>
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" size="sm" class="h-8">
							{INTEREST_SORTS.find((s) => s.value === sort)?.label ?? 'Sort'}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end">
					{#each INTEREST_SORTS as option (option.value)}
						<DropdownMenu.CheckboxItem
							checked={sort === option.value}
							onCheckedChange={() => {
								sort = option.value;
								page = 1;
							}}>{option.label}</DropdownMenu.CheckboxItem
						>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>

			{#if filtered}
				<Button
					variant="ghost"
					size="sm"
					class="h-8"
					onclick={() => {
						q = '';
						sources = [];
						kinds = [];
						page = 1;
					}}>Clear</Button
				>
			{/if}
		</div>

		{#each suggestions as suggestion (suggestion.query)}
			<SuggestionRow
				{suggestion}
				{projectId}
				onDone={(s) => (suggestions = suggestions.filter((x) => x.query !== s.query))}
			/>
		{/each}

		{#if summary?.stale}
			<p class="border-b bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
				A rule changed since this scan was labelled. Refreshing in the background.
			</p>
		{/if}

		{#if loading && !data}
			<div class="flex flex-col gap-3 p-4">
				{#each Array(6) as _, i (i)}
					<Skeleton class="h-14 w-full" />
				{/each}
			</div>
		{:else if error}
			<EmptyState icon={Eye} title="Could not load this list" description={error} class="py-12">
				<Button variant="outline" size="sm" onclick={run}>Try again</Button>
			</EmptyState>
		{:else if !data?.rows.length}
			<EmptyState
				icon={Eye}
				title={filtered || band !== ALL ? 'Nothing matches these filters' : 'Nothing stands out'}
				description={filtered || band !== ALL
					? 'Widen the filters to see the rest of the list.'
					: 'No rule, correlation or judgement flagged an asset on this scan.'}
				class="py-14"
			/>
		{:else}
			<div class="divide-y">
				{#each data.rows as row, i (row.subdomain_id)}
					<InterestRowItem
						{row}
						rank={(page - 1) * PAGE_SIZE + i + 1}
						onOpen={(r) => (selected = r)}
						onKind={pickKind}
						onDismiss={dismiss}
						onHost={() => openInAssets(row)}
					/>
				{/each}
			</div>
			<div class="border-t px-4 py-2">
				<ResultsPagination
					total={data.total}
					{page}
					pageSize={PAGE_SIZE}
					noun="asset"
					plural="assets"
					onPage={(p) => (page = p)}
				/>
			</div>
		{/if}

		{#if summary && (summary.judged_at || summary.dismissed > 0)}
			<div
				class="flex flex-wrap items-center gap-x-4 gap-y-1 border-t bg-muted/30 px-4 py-2 text-xs text-muted-foreground"
			>
				{#if summary.judged_at}
					<span class="flex items-center gap-1.5">
						<Sparkle class="size-3 text-info" />
						{summary.judged_hosts.toLocaleString()} judged by {summary.model ?? 'AI'}
						{relativeTime(summary.judged_at)}
					</span>
				{/if}
				{#if summary.dismissed > 0}
					<span>{summary.dismissed} dismissed on this target</span>
				{/if}
			</div>
		{/if}
	</Card.Root>
</div>

<InterestDetailSheet
	row={selected}
	open={selected !== null}
	onOpenChange={(v) => {
		if (!v) selected = null;
	}}
	onDismiss={dismiss}
	onOpenAssets={openInAssets}
/>
