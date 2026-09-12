<script lang="ts">
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import GitCompareArrows from '@lucide/svelte/icons/git-compare-arrows';
	import Link2 from '@lucide/svelte/icons/link-2';
	import Play from '@lucide/svelte/icons/play';

	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import CompareUnavailable from '$lib/components/scans/compare/compare-unavailable.svelte';
	import RunHeader from '$lib/components/scans/compare/run-header.svelte';
	import VerdictBanner from '$lib/components/scans/compare/verdict-banner.svelte';
	import DimensionStrip from '$lib/components/scans/compare/dimension-strip.svelte';
	import VerbFilter from '$lib/components/scans/compare/verb-filter.svelte';
	import ChangeDiff from '$lib/components/scans/compare/change-diff.svelte';
	import ChangeLedger from '$lib/components/scans/compare/change-ledger.svelte';
	import ChangeSheet from '$lib/components/scans/compare/change-sheet.svelte';

	import { compareApi } from '$lib/api/compare';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { rechecks } from '$lib/stores/rechecks.svelte';
	import { seedKindFor } from '$lib/utilities/rechecks';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import { durationText } from '$lib/utilities/scan-status';
	import { ROUTES } from '$lib/config/routes';
	import { cn } from '$lib/utils';
	import {
		COMPARE_DIGEST_SIZE,
		COMPARE_MODES,
		COMPARE_PAGE_SIZE,
		COMPARE_TAB_ALL,
		type CompareMode
	} from '$lib/config/compare';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import {
		CHANGE_VERB,
		COMPARABILITY,
		LISTED_VERBS,
		listedCount,
		type ChangeRow,
		type ChangeVerb,
		type ComparableRun,
		type ScanComparison
	} from '$lib/types/compare';

	const RESCANNABLE = ['web_assets', 'ips'];

	let comparison = $state<ScanComparison | null>(null);
	let runs = $state<ComparableRun[]>([]);
	let runsLoading = $state(false);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let rows = $state<ChangeRow[]>([]);
	let rowTotal = $state(0);
	let rowsLoading = $state(false);
	let digest = $state(false);

	let sheetOpen = $state(false);
	let sheetIndex = $state(0);
	let rescanOpen = $state(false);

	let currentId = $derived(page.url.searchParams.get('current') ?? '');
	let baselineId = $derived(page.url.searchParams.get('baseline'));
	let projectId = $derived(projectsStore.activeProject?.id ?? '');

	let activeTab = $state(COMPARE_TAB_ALL);
	let activeVerbs = $state<ChangeVerb[]>([...LISTED_VERBS]);
	let pageNumber = $state(1);
	let mode = $state<CompareMode>('ledger');

	let delta = $derived(comparison?.dimensions.find((d) => d.dimension === activeTab) ?? null);
	let covered = $derived(delta ? delta.verdict.comparability !== COMPARABILITY.NOT_COVERED : true);
	let confirmed = $derived(delta ? delta.verdict.confirmed : everyConfirmed());
	let selectedRow = $derived(rows[sheetIndex] ?? null);

	function everyConfirmed(): boolean {
		return (comparison?.dimensions ?? []).every((d) => d.verdict.confirmed);
	}

	function verbCounts(): Record<ChangeVerb, number> {
		const out = {
			[CHANGE_VERB.APPEARED]: 0,
			[CHANGE_VERB.CHANGED]: 0,
			[CHANGE_VERB.DISAPPEARED]: 0,
			[CHANGE_VERB.UNCONFIRMED]: 0,
			[CHANGE_VERB.UNCHANGED]: 0
		};
		const source = delta ? [delta] : (comparison?.dimensions ?? []);
		for (const d of source) {
			out.appeared += d.appeared;
			out.changed += d.changed;
			out.disappeared += d.disappeared;
			out.unconfirmed += d.unconfirmed;
			out.unchanged += d.unchanged;
		}
		return out;
	}

	let counts = $derived(verbCounts());
	let totalChanges = $derived(comparison?.changes_total ?? 0);
	let apart = $derived.by(() => {
		const a = comparison?.baseline.started_at;
		const b = comparison?.current.started_at;
		if (!a || !b) return '';
		const seconds = Math.abs(new Date(b).getTime() - new Date(a).getTime()) / 1000;
		return `${durationText(seconds)} apart`;
	});

	// ---------- url state ----------

	function syncUrl() {
		const sp = new SvelteURLSearchParams(page.url.searchParams);
		sp.set('current', currentId);
		if (baselineId) sp.set('baseline', baselineId);
		if (activeTab === COMPARE_TAB_ALL) sp.delete('dim');
		else sp.set('dim', activeTab);
		sp.delete('verb');
		if (activeVerbs.length !== LISTED_VERBS.length) {
			for (const v of activeVerbs) sp.append('verb', v);
		}
		if (pageNumber > 1) sp.set('page', String(pageNumber));
		else sp.delete('page');
		if (mode === 'diff') sp.set('mode', mode);
		else sp.delete('mode');
		replaceState(`${page.url.pathname}?${sp.toString()}`, page.state);
	}

	function readUrl() {
		const sp = page.url.searchParams;
		const dim = sp.get('dim');
		activeTab = dim && SURFACE_ORDER.some((s) => s.key === dim) ? dim : COMPARE_TAB_ALL;
		const verbs = sp.getAll('verb').filter((v) => LISTED_VERBS.includes(v as ChangeVerb));
		activeVerbs = verbs.length ? (verbs as ChangeVerb[]) : [...LISTED_VERBS];
		pageNumber = Math.max(1, Number(sp.get('page') ?? 1) || 1);
		const asked = sp.get('mode');
		mode = COMPARE_MODES.includes(asked as CompareMode) ? (asked as CompareMode) : 'ledger';
	}

	// ---------- loading ----------

	async function loadComparison() {
		if (!currentId || !projectId) return;
		loading = true;
		error = null;
		try {
			comparison = await compareApi.comparison(projectId, currentId, baselineId);
			if (
				activeTab !== COMPARE_TAB_ALL &&
				!comparison.dimensions.some((d) => d.dimension === activeTab)
			) {
				activeTab = COMPARE_TAB_ALL;
			}
		} catch (e) {
			comparison = null;
			error = e instanceof Error ? e.message : 'Comparison not loaded.';
		} finally {
			loading = false;
		}
	}

	async function loadRuns() {
		if (!currentId || !projectId) return;
		runsLoading = true;
		try {
			runs = await compareApi.comparable(projectId, currentId);
		} catch {
			runs = [];
		} finally {
			runsLoading = false;
		}
	}

	async function loadRows() {
		if (!comparison || !currentId || !projectId || mode === 'diff') return;
		if (!activeVerbs.length) {
			rows = [];
			rowTotal = 0;
			return;
		}
		rowsLoading = true;
		const baseline = comparison.baseline.scan_id;
		try {
			if (activeTab === COMPARE_TAB_ALL) {
				digest = true;
				const wanted = comparison.dimensions.filter(
					(d) => d.verdict.comparability !== COMPARABILITY.NOT_COVERED && listedCount(d) > 0
				);
				const pages = await Promise.all(
					wanted.map((d) =>
						compareApi.rows({
							projectId,
							current: currentId,
							baseline,
							dimension: d.dimension,
							verbs: activeVerbs,
							size: COMPARE_DIGEST_SIZE
						})
					)
				);
				const merged = pages
					.flatMap((p) => p.items)
					.sort((a, b) => a.rank - b.rank || a.title.localeCompare(b.title));
				rowTotal = pages.reduce((n, p) => n + p.total, 0);
				rows = merged.slice(0, COMPARE_DIGEST_SIZE);
			} else {
				digest = false;
				const result = await compareApi.rows({
					projectId,
					current: currentId,
					baseline,
					dimension: activeTab,
					verbs: activeVerbs,
					page: pageNumber,
					size: COMPARE_PAGE_SIZE
				});
				rows = result.items;
				rowTotal = result.total;
			}
		} catch (e) {
			rows = [];
			rowTotal = 0;
			toast.error(e instanceof Error ? e.message : 'Changes not loaded.');
		} finally {
			rowsLoading = false;
		}
	}

	// ---------- actions ----------

	function setMode(next: CompareMode) {
		if (mode === next) return;
		mode = next;
		sheetOpen = false;
		syncUrl();
		void loadRows();
	}

	function selectTab(key: string) {
		activeTab = key;
		pageNumber = 1;
		sheetOpen = false;
		syncUrl();
		void loadRows();
	}

	function toggleVerb(verb: ChangeVerb) {
		activeVerbs = activeVerbs.includes(verb)
			? activeVerbs.filter((v) => v !== verb)
			: [...activeVerbs, verb];
		pageNumber = 1;
		syncUrl();
		void loadRows();
	}

	function goPage(next: number) {
		pageNumber = next;
		sheetOpen = false;
		syncUrl();
		void loadRows();
	}

	function pick(side: 'baseline' | 'current', scanId: string) {
		const next =
			side === 'current'
				? ROUTES.compare(scanId, comparison?.baseline.scan_id ?? null)
				: ROUTES.compare(currentId, scanId);
		void goto(next);
	}

	function swap() {
		if (!comparison) return;
		void goto(ROUTES.compare(comparison.baseline.scan_id, comparison.current.scan_id));
	}

	function openRow(row: ChangeRow) {
		sheetIndex = rows.findIndex((r) => r.dimension + r.key === row.dimension + row.key);
		sheetOpen = true;
	}

	function step(dir: -1 | 1) {
		const next = sheetIndex + dir;
		if (next >= 0 && next < rows.length) sheetIndex = next;
	}

	async function copyLink() {
		await writeClipboard(window.location.href);
		toast.success('Link copied');
	}

	function onKey(event: KeyboardEvent) {
		const el = event.target as HTMLElement | null;
		if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return;
		if (event.metaKey || event.ctrlKey || event.altKey) return;
		if (event.key === 'j') {
			event.preventDefault();
			if (!sheetOpen && rows.length) {
				sheetIndex = 0;
				sheetOpen = true;
			} else step(1);
		} else if (event.key === 'k') {
			event.preventDefault();
			step(-1);
		} else if (event.key === 's' && comparison) {
			event.preventDefault();
			swap();
		}
	}

	// ---------- rescan ----------

	let rescanAssets = $derived(
		activeTab !== COMPARE_TAB_ALL && RESCANNABLE.includes(activeTab)
			? [
					...new Set(
						rows
							.filter(
								(r) => r.verb !== CHANGE_VERB.DISAPPEARED && r.verb !== CHANGE_VERB.UNCONFIRMED
							)
							.map((r) => (r.dimension === 'services' ? r.title.split(':')[0] : r.title))
					)
				].slice(0, rechecks.schema?.max_assets || 500)
			: []
	);

	let rescanSeed = $derived(
		comparison && rescanAssets.length
			? {
					selection: {
						dimension: activeTab,
						picks: rescanAssets.map((value) => ({
							value,
							scan_id: comparison!.current.scan_id
						})),
						exclude: []
					},
					dimension: activeTab,
					targetType: comparison.target_type,
					seedKind: seedKindFor(rechecks.schema, activeTab),
					assets: rescanAssets
				}
			: null
	);

	// ---------- effects ----------

	$effect(() => {
		void currentId;
		void baselineId;
		void projectId;
		untrack(() => {
			readUrl();
			void rechecks.loadSchema();
			void loadRuns();
			void loadComparison().then(() => loadRows());
		});
	});

	$effect(() => {
		breadcrumbStore.set('compare', 'Compare runs');
	});
</script>

<svelte:window onkeydown={onKey} />

<svelte:head>
	<title
		>{comparison ? `Compare runs · ${comparison.target_value}` : 'Compare runs'} · reNgine</title
	>
</svelte:head>

<div class="flex min-h-0 flex-col">
	{#if loading}
		<div class="flex flex-col gap-4 p-5">
			<Skeleton class="h-8 w-64" />
			<Skeleton class="h-28" />
			<Skeleton class="h-24" />
			<Skeleton class="h-64" />
		</div>
	{:else if error || !comparison}
		<CompareUnavailable
			reason={error ?? 'Pick two finished runs of the same target.'}
			{currentId}
			{runs}
			loading={runsLoading}
		/>
	{:else}
		<div class="flex flex-wrap items-center gap-2 px-4 py-3 sm:px-5">
			<Button
				variant="ghost"
				size="sm"
				href={ROUTES.scan(comparison.current.scan_id)}
				class="-ml-2 gap-1.5"
			>
				<ArrowLeft class="size-4" />
				Back to run
			</Button>
			<span class="flex items-center gap-2 text-sm">
				<GitCompareArrows class="size-4 text-muted-foreground" />
				<span class="font-medium">{comparison.target_value}</span>
			</span>
			<div class="ml-auto flex flex-wrap items-center gap-2">
				<div class="flex rounded-md border p-0.5" role="group" aria-label="View">
					{#each COMPARE_MODES as key (key)}
						<button
							type="button"
							aria-pressed={mode === key}
							onclick={() => setMode(key)}
							class={cn(
								'rounded px-2.5 py-1 text-xs font-medium capitalize transition-colors',
								mode === key
									? 'bg-accent text-foreground'
									: 'text-muted-foreground hover:text-foreground'
							)}
						>
							{key}
						</button>
					{/each}
				</div>
				{#if rescanSeed}
					<Button variant="outline" size="sm" class="gap-1.5" onclick={() => (rescanOpen = true)}>
						<Play class="size-3.5" />
						Rescan {rescanAssets.length}
						{rescanAssets.length === 1 ? 'asset' : 'assets'}
					</Button>
				{/if}
				<Button variant="outline" size="sm" class="gap-1.5" onclick={copyLink}>
					<Link2 class="size-3.5" />
					Copy link
				</Button>
			</div>
		</div>

		<div class="border-y">
			<RunHeader
				baseline={comparison.baseline}
				current={comparison.current}
				{runs}
				loading={runsLoading}
				onPick={pick}
				onSwap={swap}
			/>
		</div>

		<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1 px-4 pt-4 pb-3 sm:px-5">
			<h1 class="text-xl font-semibold tracking-tight">{comparison.headline}</h1>
			<span class="flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
				{#if totalChanges > 0}
					<span>highest signal first</span>
				{/if}
				{#if apart}
					{#if totalChanges > 0}<span class="opacity-40">·</span>{/if}
					<span class="tabular-nums">{apart}</span>
				{/if}
			</span>
		</div>

		<VerdictBanner {comparison} />

		<DimensionStrip
			dimensions={comparison.dimensions}
			total={totalChanges}
			active={activeTab}
			onSelect={selectTab}
		/>

		<VerbFilter {counts} active={activeVerbs} {confirmed} onToggle={toggleVerb} />

		{#if mode === 'diff'}
			<ChangeDiff
				{projectId}
				current={comparison.current.scan_id}
				baseline={comparison.baseline.scan_id}
				dimension={activeTab}
				verbs={activeVerbs}
				filename="{comparison.target_value}-compare.diff"
			/>
		{:else}
			<ChangeLedger
				{rows}
				total={rowTotal}
				page={pageNumber}
				size={COMPARE_PAGE_SIZE}
				loading={rowsLoading}
				{digest}
				showDimension={activeTab === COMPARE_TAB_ALL}
				{covered}
				notCoveredNote={delta?.verdict.note ?? ''}
				anyVerbOn={activeVerbs.length > 0}
				selectedKey={sheetOpen && selectedRow ? selectedRow.dimension + selectedRow.key : null}
				noun={delta?.noun ?? 'change'}
				nounPlural={delta?.noun_plural ?? 'changes'}
				onOpen={openRow}
				onPage={goPage}
			/>
		{/if}

		<ChangeSheet
			row={selectedRow}
			baseline={comparison.baseline}
			current={comparison.current}
			open={sheetOpen}
			index={sheetIndex}
			total={rows.length}
			onOpenChange={(v) => (sheetOpen = v)}
			onStep={step}
		/>

		<LaunchDialog open={rescanOpen} rescan={rescanSeed} onClose={() => (rescanOpen = false)} />
	{/if}
</div>
