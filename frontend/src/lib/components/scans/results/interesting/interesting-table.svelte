<script lang="ts">
	import { goto } from '$app/navigation';
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { onDestroy, untrack } from 'svelte';
	import { LiveRefresh } from '$lib/utilities/live-results';
	import { afterPause } from '$lib/utilities/debounce';
	import Search from '@lucide/svelte/icons/search';
	import Sparkle from '@lucide/svelte/icons/sparkle';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Eye from '@lucide/svelte/icons/eye';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import Copy from '@lucide/svelte/icons/copy';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import { Button } from '$lib/components/ui/button';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Badge } from '$lib/components/ui/badge';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import type { TableColumn } from '../table/columns';
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
	import {
		INTEREST_SOURCE,
		type InterestPage,
		type InterestRow,
		type RuleSuggestion
	} from '$lib/types/interest';
	import { exactToken } from '$lib/utilities/scan-insights';
	import type { TargetScope } from '$lib/utilities/surface-scope';
	import SelectionActionBar from '$lib/components/selection-action-bar.svelte';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { SvelteMap } from 'svelte/reactivity';
	import InterestRowItem from './interest-row.svelte';
	import InterestDetailSheet from './interest-detail-sheet.svelte';
	import SuggestionRow from './suggestion-row.svelte';

	interface Props {
		scanId?: string;
		projectId: string;
		projectWide?: boolean;
		active: boolean;
		onTab?: (tab: ResultTab, filter?: string) => void;
		revision?: number;
		onTotal?: (total: number) => void;
		initialBand?: string | null;
		initialKinds?: string[];
		scope?: TargetScope;
	}

	let {
		scanId = '',
		projectId,
		projectWide = false,
		active,
		revision = 0,
		onTab,
		onTotal,
		initialBand = null,
		initialKinds = [],
		scope = {}
	}: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	const INTEREST_SKELETON_COLUMNS: TableColumn[] = [
		{ key: 'asset', label: '', width: 'min-w-0 flex-1' },
		{ key: 'signals', label: '', width: 'hidden w-48 shrink-0 sm:flex' }
	];

	const PAGE_SIZE = 25;
	const ALL = 'all';
	const STALE_RETRY_MS = 5000;

	let data = $state<InterestPage | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let band = $state(untrack(() => initialBand) || ALL);
	let q = $state('');
	let applied = $state('');
	let sources = $state<string[]>([]);
	let kinds = $state<string[]>(untrack(() => [...initialKinds]));
	let sort = $state<string>(INTEREST_SORTS[0].value);
	let sortLabel = $derived(INTEREST_SORTS.find((s) => s.value === sort)?.label ?? 'Sort');
	let page = $state(1);
	let judging = $state(false);
	let retry: ReturnType<typeof setTimeout> | null = null;
	let suggestions = $state<RuleSuggestion[]>([]);
	let askedFor = '';
	let selected = $state<InterestRow | null>(null);
	let loaded = false;
	const picked = new SvelteMap<string, InterestRow>();
	let dismissing = $state(false);
	let req = 0;

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
		if (!active) return;
		untrack(() => interestCatalog.load());
	});

	$effect(() => {
		const next = q.trim();
		return afterPause(() => {
			if (applied !== next) applied = next;
		});
	});

	let signature = $derived(
		JSON.stringify({ scanId, band, q: applied, sources, kinds, sort, page })
	);

	$effect(() => {
		void signature;
		if (projectWide ? !projectId : !scanId) return;
		if (loaded && !active) return;
		loaded = true;
		void run();
	});

	$effect(() => {
		const s = summary;
		if (projectWide || !active || !s?.ai_enabled || !s.judged_hosts || askedFor === scanId) return;
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

	async function run(quiet = false): Promise<void> {
		const my = ++req;
		if (!quiet) loading = true;
		try {
			const filter = {
				q: applied || null,
				bands: band === ALL ? [] : [band],
				sources,
				kinds,
				sort,
				order: sort === 'host' ? 'asc' : 'desc',
				limit: PAGE_SIZE,
				offset: (page - 1) * PAGE_SIZE
			};
			const result = projectWide
				? await interestApi.project(projectId, filter, scope)
				: await interestApi.scan(scanId, filter);
			if (my !== req) return;
			data = result;
			error = null;
			onTotal?.(result.summary.total);
			if (result.summary.stale && retry === null) {
				retry = setTimeout(() => {
					retry = null;
					void run();
				}, STALE_RETRY_MS);
			}
		} catch (e) {
			if (my === req) error = e instanceof Error ? e.message : 'Exposures not loaded';
		} finally {
			if (my === req) loading = false;
		}
	}

	const liveRefresh = new LiveRefresh(() => run(true));
	$effect(() => {
		liveRefresh.notify(revision, active ?? true);
	});
	onDestroy(() => liveRefresh.stop());

	function toggle(list: string[], value: string): string[] {
		return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
	}

	async function judge(): Promise<void> {
		judging = true;
		try {
			await interestApi.judge(scanId);
			toast.success('Judging started');
		} catch {
			toast.error('Judging not started');
		} finally {
			judging = false;
		}
	}

	async function dismiss(row: InterestRow): Promise<void> {
		try {
			await interestApi.dismiss({ host: row.host, target_id: row.target_id });
			toast.success(`${row.host} dismissed`);
			await run();
		} catch {
			toast.error(`${row.host} not dismissed`);
		}
	}

	function toggleCheck(row: InterestRow): void {
		if (picked.has(row.subdomain_id)) picked.delete(row.subdomain_id);
		else picked.set(row.subdomain_id, row);
	}

	async function dismissPicked(): Promise<void> {
		const rows = [...picked.values()];
		if (!rows.length) return;
		dismissing = true;
		try {
			const result = await interestApi.dismissMany(
				rows.map((row) => ({ host: row.host, target_id: row.target_id }))
			);
			picked.clear();
			toast.success(
				`${result.dismissed.toLocaleString()} ${result.dismissed === 1 ? 'exposure' : 'exposures'} dismissed`
			);
			await run();
		} catch {
			toast.error('Exposures not dismissed');
		} finally {
			dismissing = false;
		}
	}

	async function copyPicked(): Promise<void> {
		const names = [...picked.values()].map((row) => row.host);
		if (!names.length) return;
		if (await writeClipboard(names.join('\n')))
			toast.success(`${names.length.toLocaleString()} web assets copied`);
		else toast.error('Clipboard not available');
	}

	function pickKind(kind: string): void {
		kinds = toggle(kinds, kind);
		page = 1;
	}

	$effect(() => () => {
		if (retry !== null) clearTimeout(retry);
	});

	function openInAssets(row: InterestRow): void {
		const filter = exactToken('host', row.host);
		if (onTab) onTab(WEB.tab, filter);
		else void goto(ROUTES.surface(WEB.tab, { [WEB.queryParam]: filter }));
	}
</script>

<div class="flex flex-col gap-4">
	<Card.Root class="gap-0 overflow-hidden py-0">
		<div class="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
			<div class="flex min-w-0 flex-col gap-0.5">
				{#if !projectWide}
					<h2 class="text-base leading-6 font-semibold">Exposures</h2>
				{/if}
				{#if summary && summary.total > 0}
					<p class="text-xs text-muted-foreground">
						{summary.total.toLocaleString()}
						{summary.total === 1 ? WEB.noun : WEB.nounPlural} flagged
						{#each activeSources as s (s.key)}{` · ${(summary.sources[s.key] ?? 0).toLocaleString()} ${
								s.key === INTEREST_SOURCE.AI ? 'judged by AI' : `from ${s.label.toLowerCase()}`
							}`}{/each}
					</p>
				{/if}
			</div>
			<div class="flex min-w-0 flex-wrap items-center gap-2">
				{#if !projectWide && summary?.ai_enabled}
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
				{:else if !projectWide && summary?.ai_available}
					<Hint text="Asset judgement is off. Enable it on the AI page.">
						{#snippet child(props)}
							<Button {...props} variant="outline" size="sm" href={ROUTES.ai('features')}>
								<Sparkle class="size-3.5" />
								Enable AI judgement
							</Button>
						{/snippet}
					</Hint>
				{/if}
				{#if !projectWide}
					<Hint text="Rules, keywords and notifications">
						{#snippet child(props)}
							<Button {...props} variant="ghost" size="sm" href={ROUTES.exposures('rules')}>
								Manage rules
							</Button>
						{/snippet}
					</Hint>
				{/if}
				<Button variant="ghost" size="icon-sm" onclick={() => run()} aria-label="Refresh">
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

		<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
			<InputGroup.Root class="w-auto min-w-56 flex-1">
				<InputGroup.Addon><Search /></InputGroup.Addon>
				<InputGroup.Input
					bind:value={q}
					placeholder="Filter by hostname"
					aria-label="Filter by hostname"
					oninput={() => (page = 1)}
				/>
			</InputGroup.Root>

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							class={kinds.length ? 'border-primary/50 bg-primary/5' : ''}
						>
							<SlidersHorizontal />
							Reason
							{#if kinds.length}
								<Badge variant="secondary" class="h-5 px-1.5 text-xs">{kinds.length}</Badge>
							{/if}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="start" class="w-64">
					{#each activeKinds as k (k.key)}
						{@const Icon = kindIcon(k.key)}
						<DropdownMenu.CheckboxItem
							checked={kinds.includes(k.key)}
							onCheckedChange={() => pickKind(k.key)}
							closeOnSelect={false}
						>
							<Icon class="size-3.5 text-muted-foreground" />
							<span class="flex-1 truncate">{k.label}</span>
							<span class="text-xs tabular-nums text-muted-foreground"
								>{(summary?.kinds?.[k.key] ?? 0).toLocaleString()}</span
							>
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="outline"
							class={sources.length ? 'border-primary/50 bg-primary/5' : ''}
						>
							Flagged by
							{#if sources.length}
								<Badge variant="secondary" class="h-5 px-1.5 text-xs">{sources.length}</Badge>
							{/if}
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
							closeOnSelect={false}
						>
							<Icon class="size-3.5 text-muted-foreground" />
							<span class="flex-1 truncate">{s.label}</span>
							<span class="text-xs tabular-nums text-muted-foreground"
								>{(summary?.sources?.[s.key] ?? 0).toLocaleString()}</span
							>
						</DropdownMenu.CheckboxItem>
					{/each}
				</DropdownMenu.Content>
			</DropdownMenu.Root>

			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="outline" aria-label="Sort by {sortLabel}">
							{sortLabel}
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end">
					<DropdownMenu.RadioGroup
						value={sort}
						onValueChange={(v) => {
							sort = v;
							page = 1;
						}}
					>
						{#each INTEREST_SORTS as option (option.value)}
							<DropdownMenu.RadioItem value={option.value}>{option.label}</DropdownMenu.RadioItem>
						{/each}
					</DropdownMenu.RadioGroup>
				</DropdownMenu.Content>
			</DropdownMenu.Root>

			{#if filtered}
				<Button
					variant="ghost"
					onclick={() => {
						q = '';
						applied = '';
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
				A rule changed after the last evaluation. Refreshing.
			</p>
		{/if}

		{#if loading && !data}
			<TableSkeleton lead={INTEREST_SKELETON_COLUMNS} header={false} actions={false} rows={6} />
		{:else if error}
			<EmptyState
				icon={TriangleAlert}
				title="Exposures not loaded"
				description={error}
				class="rounded-none border-0 bg-transparent py-16"
			>
				<Button variant="outline" size="sm" onclick={() => run()}>Retry</Button>
			</EmptyState>
		{:else if !data?.rows.length}
			<EmptyState
				icon={Eye}
				title={filtered || band !== ALL ? 'No exposures match' : 'No exposures'}
				class="rounded-none border-0 bg-transparent py-16"
			/>
		{:else}
			<div class="divide-y">
				{#each data.rows as row, i (row.subdomain_id)}
					<InterestRowItem
						{row}
						rank={(page - 1) * PAGE_SIZE + i + 1}
						checked={picked.has(row.subdomain_id)}
						onCheck={toggleCheck}
						onOpen={(r) => (selected = r)}
						onKind={pickKind}
						onDismiss={dismiss}
					/>
				{/each}
			</div>
			<div class="border-t px-4 py-2">
				<ResultsPagination
					total={data.total}
					page={page - 1}
					pageSize={PAGE_SIZE}
					noun={WEB.noun}
					plural={WEB.nounPlural}
					onPage={(p) => (page = p + 1)}
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
					<span>{summary.dismissed.toLocaleString()} dismissed</span>
				{/if}
			</div>
		{/if}
	</Card.Root>
</div>

<SelectionActionBar selectedCount={picked.size} noun="exposure" onClear={() => picked.clear()}>
	<LoadingButton
		variant="ghost"
		size="sm"
		loading={dismissing}
		loadingLabel="Dismissing"
		onclick={dismissPicked}
	>
		<EyeOff class="h-3.5 w-3.5 text-muted-foreground" />
		Dismiss
	</LoadingButton>
	<Button variant="ghost" size="sm" onclick={copyPicked}>
		<Copy class="h-3.5 w-3.5 text-muted-foreground" />
		Copy web assets
	</Button>
</SelectionActionBar>

<InterestDetailSheet
	row={selected}
	open={selected !== null}
	onOpenChange={(v) => {
		if (!v) selected = null;
	}}
	onDismiss={dismiss}
	onOpenAssets={openInAssets}
/>
