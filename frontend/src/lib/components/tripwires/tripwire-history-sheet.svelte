<script lang="ts">
	import { untrack } from 'svelte';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import * as Sheet from '$lib/components/ui/sheet';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Switch } from '$lib/components/ui/switch';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import Zap from '@lucide/svelte/icons/zap';
	import { tripwiresApi } from '$lib/api/tripwires';
	import { ROUTES } from '$lib/config/routes';
	import {
		CHECK_STATUS_VARIANT,
		FIRE_ON_VERB,
		RECENT_DAYS,
		CheckStatus,
		checkStatusLabel,
		dimensionSpec,
		FireOn,
		fireOnLabel,
		OutcomeStatus,
		triggerLabel
	} from '$lib/config/tripwires';
	import type { Outcome, Tripwire, TripwireRun, TripwireRunCounts } from '$lib/types/tripwire';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
	import { scopeText } from './format';
	import QueryChip from './query-chip.svelte';

	interface Props {
		tripwire: Tripwire | null;
		projectId: string;
		focusRunId?: string | null;
		onOpenChange: (open: boolean) => void;
		onEdit: (tripwire: Tripwire) => void;
		onToggle: (tripwire: Tripwire, enabled: boolean) => void;
	}

	let { tripwire, projectId, focusRunId = null, onOpenChange, onEdit, onToggle }: Props = $props();

	const PAGE_SIZE = 20;
	const TABS = [
		{ key: CheckStatus.Fired, label: 'Fired' },
		{ key: CheckStatus.Quiet, label: 'Not fired' },
		{ key: 'all', label: 'All' }
	];

	let tab = $state<string>(CheckStatus.Fired);
	let page = $state(1);
	let runs = $state<TripwireRun[]>([]);
	let total = $state(0);
	let counts = $state<TripwireRunCounts | null>(null);
	let loading = $state(false);
	let expanded = $state<string | null>(null);
	let loadedFor = $state<string | null>(null);
	let pinned = $state<TripwireRun | null>(null);

	let spec = $derived(tripwire ? dimensionSpec(tripwire.dimension) : null);
	let verb = $derived(tripwire ? (FIRE_ON_VERB[tripwire.fire_on as FireOn] ?? 'fired') : 'fired');
	let tabCounts = $derived(
		counts
			? { [CheckStatus.Fired]: counts.fired, [CheckStatus.Quiet]: counts.quiet, all: counts.total }
			: null
	);
	let shown = $derived.by(() => {
		const focus = pinned;
		if (!focus || page !== 1 || (tab !== 'all' && tab !== focus.status)) return runs;
		return runs.some((r) => r.id === focus.id) ? runs : [focus, ...runs];
	});

	$effect(() => {
		const row = tripwire;
		if (!row) {
			loadedFor = null;
			return;
		}
		if (loadedFor === row.id) return;
		untrack(() => {
			loadedFor = row.id;
			tab = CheckStatus.Fired;
			page = 1;
			expanded = focusRunId;
			pinned = null;
			const focus = focusRunId;
			void loadCounts(row.id);
			void load(row.id).then(() => {
				if (focus && loadedFor === row.id && !runs.some((r) => r.id === focus)) {
					void loadFocus(row.id, focus);
				}
			});
		});
	});

	async function loadFocus(id: string, runId: string) {
		try {
			const run = await tripwiresApi.run(runId, projectId);
			if (loadedFor === id && run.tripwire_id === id) pinned = run;
		} catch {
			pinned = null;
		}
	}

	async function loadCounts(id: string) {
		try {
			counts = await tripwiresApi.runCounts(id, projectId);
		} catch {
			counts = null;
		}
	}

	async function load(id: string) {
		loading = true;
		try {
			const res = await tripwiresApi.runs(id, projectId, {
				status: tab === 'all' ? null : tab,
				page,
				size: PAGE_SIZE
			});
			runs = res.items;
			total = res.total;
		} catch {
			runs = [];
			total = 0;
		} finally {
			loading = false;
		}
	}

	function setTab(key: string) {
		tab = key;
		page = 1;
		if (tripwire) void load(tripwire.id);
	}

	function setPage(next: number) {
		page = next;
		if (tripwire) void load(tripwire.id);
	}

	function outcomeTone(o: Outcome): string {
		if (o.status === OutcomeStatus.Done) return 'bg-success';
		if (o.status === OutcomeStatus.Failed) return 'bg-destructive';
		return 'border border-muted-foreground/50';
	}

	function resultsHref(run: TripwireRun): string {
		if (!tripwire || !spec) return '';
		const query =
			tripwire.fire_on === FireOn.Appears
				? `${tripwire.query.trim() ? `(${tripwire.query.trim()}) ` : ''}is:new`
				: tripwire.query;
		return ROUTES.results(spec.tab, run.scan_id, query ? { [spec.queryParam]: query } : undefined);
	}

	function resultsLabel(run: TripwireRun): string {
		if (!tripwire || !spec) return '';
		const appears = tripwire.fire_on === FireOn.Appears;
		const n = appears ? run.fired : run.matched;
		const noun = n === 1 ? spec.noun : spec.nounPlural;
		return appears
			? `Open ${n.toLocaleString()} ${noun} that appeared`
			: `Open ${n.toLocaleString()} matching ${noun}`;
	}
</script>

<Sheet.Root open={tripwire !== null} {onOpenChange}>
	<Sheet.Content side="right" class="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
		{#if tripwire && spec}
			<Sheet.Header class="gap-2 border-b px-5 py-4">
				<div class="flex items-center gap-3 pr-8">
					<Sheet.Title class="min-w-0 flex-1 truncate">{tripwire.name}</Sheet.Title>
					<Switch
						checked={tripwire.enabled}
						onCheckedChange={(v) => onToggle(tripwire, v)}
						aria-label={tripwire.enabled ? 'Pause tripwire' : 'Resume tripwire'}
					/>
					<Button variant="outline" size="sm" onclick={() => onEdit(tripwire)}>Edit</Button>
				</div>
				<Sheet.Description class="flex flex-wrap items-center gap-x-2 gap-y-1">
					<span>{spec.label}</span>
					<QueryChip dimension={tripwire.dimension} query={tripwire.query} wrap />
					<span
						>· {fireOnLabel(tripwire.fire_on)} · {scopeText(tripwire.scope, tripwire.scope.labels)} ·
						{triggerLabel(tripwire.trigger)}</span
					>
				</Sheet.Description>
			</Sheet.Header>

			<div class="grid grid-cols-3 divide-x border-b">
				<div class="flex flex-col gap-0.5 px-5 py-3">
					<span class="text-xl font-semibold tabular-nums"
						>{tripwire.recent_fired.toLocaleString()}</span
					>
					<span class="text-xs text-muted-foreground">Firings, {RECENT_DAYS} days</span>
				</div>
				<div class="flex flex-col gap-0.5 px-5 py-3">
					<span class="text-xl font-semibold tabular-nums"
						>{tripwire.fired_count.toLocaleString()}</span
					>
					<span class="text-xs text-muted-foreground">Firings, all time</span>
				</div>
				<div class="flex flex-col gap-0.5 px-5 py-3">
					<span class="text-xl font-semibold tabular-nums"
						>{(counts?.total ?? 0).toLocaleString()}</span
					>
					<span class="text-xs text-muted-foreground">Runs checked</span>
				</div>
			</div>

			<div class="border-b px-2">
				<CountTabs tabs={TABS} value={tab} counts={tabCounts} onChange={setTab} />
			</div>

			<ScrollArea class="min-h-0 flex-1">
				{#if loading && shown.length === 0}
					<RowSkeleton rows={5} class="px-5" />
				{:else if shown.length === 0}
					<EmptyState
						icon={Zap}
						title={tab === CheckStatus.Fired ? 'No firings' : 'No checks'}
						class="rounded-none border-0 bg-transparent py-16"
					/>
				{:else}
					<div class="flex flex-col divide-y divide-border/60">
						{#each shown as run (run.id)}
							{@const open = expanded === run.id}
							{@const fired = run.status === CheckStatus.Fired}
							<div class="px-5 py-3 {focusRunId === run.id ? 'bg-primary/5' : ''}">
								<button
									type="button"
									class="grid w-full grid-cols-[84px_minmax(0,1fr)_auto_auto] items-start gap-3 text-left"
									aria-expanded={open}
									onclick={() => (expanded = open ? null : run.id)}
								>
									<span class="flex flex-col gap-0.5">
										<span class="text-sm font-medium">{relativeTime(run.checked_at)}</span>
										<span class="text-2xs text-muted-foreground"
											>{formatDateTime(run.fired_at ?? run.checked_at)}</span
										>
									</span>
									<span class="flex min-w-0 flex-col gap-0.5">
										<span class="truncate font-mono text-sm">{run.target_value}</span>
										<span class="text-xs text-muted-foreground">
											{#if fired}
												{run.fired.toLocaleString()}
												{run.fired === 1 ? spec.noun : spec.nounPlural}
												{verb} · {run.matched.toLocaleString()} matching
											{:else if run.detail}
												{run.detail}
											{:else}
												{run.matched.toLocaleString()} matching
											{/if}
										</span>
									</span>
									<Badge
										variant={CHECK_STATUS_VARIANT[run.status as CheckStatus] ?? 'outline'}
										class="mt-0.5"
									>
										{checkStatusLabel(run.status)}
									</Badge>
									<ChevronDown
										class="mt-1 size-4 text-muted-foreground transition-transform {open
											? 'rotate-180'
											: ''}"
									/>
								</button>
								{#if open}
									<div class="mt-3 flex flex-col gap-3 pl-[96px]">
										{#if run.rows.length > 0}
											<div class="flex flex-col divide-y divide-border/60 rounded-md border">
												{#each run.rows.slice(0, 50) as row (row.key)}
													<div
														class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-2.5 py-1.5 text-xs"
													>
														<span class="truncate font-mono">{row.label}</span>
														{#if row.severity}
															<SeverityMark severity={row.severity} />
														{:else}
															<span class="truncate text-muted-foreground">{row.detail}</span>
														{/if}
													</div>
												{/each}
											</div>
											{#if run.fired > run.rows.length}
												<span class="text-2xs text-muted-foreground"
													>{run.rows.length} of {run.fired.toLocaleString()} shown</span
												>
											{/if}
										{/if}
										{#if run.outcomes.length > 0}
											<div class="flex flex-col gap-1.5">
												{#each run.outcomes as outcome, i (i)}
													<div class="flex items-center gap-2 text-xs">
														<span class="size-2 shrink-0 rounded-full {outcomeTone(outcome)}"
														></span>
														<span class="min-w-0 truncate">{outcome.detail}</span>
														{#if outcome.scan_id}
															<a
																href={ROUTES.scan(outcome.scan_id)}
																class="ml-auto shrink-0 text-muted-foreground hover:text-primary"
																aria-label="Open run"
															>
																<ArrowUpRight class="size-3.5" />
															</a>
														{/if}
													</div>
												{/each}
											</div>
										{/if}
										<div class="flex items-center gap-2">
											<Button variant="outline" size="sm" href={resultsHref(run)}
												>{resultsLabel(run)}</Button
											>
											<Button variant="ghost" size="sm" href={ROUTES.scan(run.scan_id)}
												>Open scan</Button
											>
										</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</ScrollArea>
			{#if total > PAGE_SIZE}
				<div class="border-t px-3">
					<ResultsPagination
						{total}
						{page}
						pageSize={PAGE_SIZE}
						noun="check"
						plural="checks"
						onPage={setPage}
					/>
				</div>
			{/if}
		{/if}
	</Sheet.Content>
</Sheet.Root>
