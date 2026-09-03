<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import * as Card from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import ScanTrendSparkline from '$lib/components/scans/scan-trend-sparkline.svelte';
	import GeoPanel from './geo-panel.svelte';
	import RunRibbon from './run-ribbon.svelte';
	import HistoryPopover from './history-popover.svelte';
	import { elapsedSeconds, formatSeconds, isLiveStatus } from '$lib/utilities/scan-status';
	import { etaLabel, plannedStages, stageProgress } from '$lib/utilities/scan-progress';
	import { targetAssetNoun, TargetType } from '$lib/types/target';
	import type { ScanActivityRead, ScanCommandRead, ScanRead } from '$lib/types/scan';
	import type { StageCatalogEntry } from '$lib/types/scan-engine';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';
	import type { InsightTally } from '$lib/utilities/scan-insights';

	export interface SurfaceStats {
		resolved: number | null;
		live: number | null;
		web: number | null;
		networks: number | null;
	}

	interface Props {
		scan: ScanRead;
		previous: ScanRead | null;
		history: ScanRead[];
		historyLoaded: boolean;
		stats: SurfaceStats;
		run: LiveRun | undefined;
		catalog: StageCatalogEntry[];
		activities: ScanActivityRead[];
		commands: ScanCommandRead[];
		previousDuration: number | null;
		now: number;
		scanId: string;
		projectId: string;
		geography: InsightTally[];
		geoTotal: number;
		geoReady: boolean;
		onTab: (tab: string, filter?: string) => void;
	}

	let {
		scan,
		previous,
		history,
		historyLoaded,
		stats,
		run,
		catalog,
		activities,
		commands,
		previousDuration,
		now,
		scanId,
		projectId,
		geography,
		geoTotal,
		geoReady,
		onTab
	}: Props = $props();

	const TREND_RUNS = 5;
	const NEW_FILTER = 'is:new';
	const fmtRun = (iso: string) =>
		new Date(iso).toLocaleString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});

	let type = $derived(scan.execution_config.target_type);
	let isDomain = $derived(type === TargetType.DOMAIN);
	let live = $derived(isLiveStatus(scan.status));
	let completed = $derived(scan.status === 'completed');
	let planned = $derived(plannedStages(scan, catalog));
	let progress = $derived(stageProgress(scan, run, planned));
	let doneCount = $derived(
		live
			? progress.done
			: planned.filter((s) => activities.some((a) => a.name === s.name && a.status === 'success'))
					.length
	);
	let elapsedSec = $derived(elapsedSeconds(scan, now));
	let eta = $derived(scan.status === 'running' ? etaLabel(previousDuration, elapsedSec) : null);
	let added = $derived(scan.new_subdomains ?? 0);
	let gone = $derived(scan.gone_subdomains ?? 0);
	let baseline = $derived(scan.is_first_scan === true || scan.prev_subdomains_found == null);
	let compared = $derived(completed && !baseline);
	let noun = (n: number) => targetAssetNoun(type, n);
	let nounPlural = $derived(targetAssetNoun(type));
	let nounTitle = $derived(nounPlural.charAt(0).toUpperCase() + nounPlural.slice(1));
	let showGeo = $derived(geography.length > 0 || live || !geoReady);

	let headline = $derived.by(() => {
		switch (scan.status) {
			case 'pending':
				return 'Scan queued';
			case 'running':
				return 'Scan in progress';
			case 'failed':
				return 'Scan failed';
			case 'cancelled':
				return 'Scan cancelled';
			default:
				if (baseline) return 'Baseline scan';
				if (added > 0) return `${added.toLocaleString()} new ${noun(added)}`;
				return gone > 0 ? `No new ${nounPlural}` : 'No change since the previous scan';
		}
	});
	let subline = $derived.by(() => {
		switch (scan.status) {
			case 'pending':
				return 'Waiting for an available worker.';
			case 'running': {
				const parts = [run?.stage ? run.stage.title : progress.label];
				parts.push(`${progress.done} of ${progress.total} stages`);
				if (elapsedSec != null) parts.push(`${formatSeconds(elapsedSec)} elapsed`);
				if (eta) parts.push(eta);
				return parts.join(' · ');
			}
			case 'failed':
				return scan.error ?? 'A stage failed. Select a stage below for details.';
			case 'cancelled':
				return `Stopped after ${doneCount} of ${planned.length} stages. Results are partial.`;
			default:
				if (baseline)
					return `First scan of ${scan.execution_config.target_value}. Later scans are compared against it.`;
				if (!historyLoaded) return '';
				if (!previous) return 'Compared with the previous completed scan.';
				return `Compared with the ${previous.engine_name} scan on ${fmtRun(previous.started_at ?? previous.created_at)}.`;
		}
	});

	type Metric = keyof Pick<
		ScanRead,
		| 'subdomains_found'
		| 'http_assets_found'
		| 'ips_found'
		| 'open_ports_found'
		| 'vulnerabilities_found'
		| 'endpoints_found'
	>;

	let runs = $derived(
		history
			.filter((s) => s.status === 'completed')
			.sort(
				(a, b) =>
					new Date(a.started_at ?? a.created_at).getTime() -
					new Date(b.started_at ?? b.created_at).getTime()
			)
			.slice(-TREND_RUNS)
	);
	const trendOf = (metric: Metric) => {
		if (runs.length < 2) return null;
		const values = runs.map((s) => s[metric]);
		return values.some((v) => v > 0) ? values : null;
	};

	interface Kpi {
		key: string;
		label: string;
		value: number | null;
		tab: string;
		filter?: string;
		added?: number;
		gone?: number;
		diff?: number | null;
		hint?: string;
		trend: number[] | null;
	}
	const diffVs = (value: number, before: number | undefined) =>
		before == null || value === before ? null : value - before;
	const pctOf = (n: number | null, of: number | null) =>
		n != null && of ? `${Math.round((n / of) * 100)}%` : null;

	let kpis = $derived.by<Kpi[]>(() => {
		const cmp = compared ? previous : null;
		const list: Kpi[] = [
			{
				key: 'assets',
				label: nounTitle,
				value: scan.subdomains_found,
				tab: 'web-assets',
				added: compared ? added : undefined,
				gone: compared ? gone : undefined,
				trend: trendOf('subdomains_found')
			}
		];
		if (isDomain) {
			const pct = pctOf(stats.resolved, scan.subdomains_found);
			list.push({
				key: 'resolved',
				label: 'Resolved',
				value: stats.resolved,
				tab: 'web-assets',
				filter: 'is:resolved',
				hint: pct ? `${pct} of ${nounPlural}` : undefined,
				trend: null
			});
		}
		const livePct = pctOf(stats.live, stats.web);
		list.push(
			{
				key: 'live',
				label: 'Live hosts',
				value: stats.live,
				tab: 'web-assets',
				filter: 'is:live',
				hint: livePct ? `${livePct} of web hosts` : undefined,
				trend: null
			},
			{
				key: 'http',
				label: 'HTTP services',
				value: scan.http_assets_found,
				tab: 'web-assets',
				filter: 'is:web',
				diff: diffVs(scan.http_assets_found, cmp?.http_assets_found),
				trend: trendOf('http_assets_found')
			},
			{
				key: 'ips',
				label: 'IP addresses',
				value: scan.ips_found,
				tab: 'ips',
				diff: diffVs(scan.ips_found, cmp?.ips_found),
				trend: trendOf('ips_found')
			},
			{
				key: 'ports',
				label: 'Open ports',
				value: scan.open_ports_found,
				tab: 'services',
				diff: diffVs(scan.open_ports_found, cmp?.open_ports_found),
				trend: trendOf('open_ports_found')
			}
		);
		if (!isDomain)
			list.push({
				key: 'networks',
				label: 'Networks',
				value: stats.networks,
				tab: 'ips',
				trend: null
			});
		if (scan.vulnerabilities_found > 0)
			list.push({
				key: 'vulns',
				label: 'Vulnerabilities',
				value: scan.vulnerabilities_found,
				tab: 'web-assets',
				trend: trendOf('vulnerabilities_found')
			});
		if (scan.endpoints_found > 0)
			list.push({
				key: 'endpoints',
				label: 'Endpoints',
				value: scan.endpoints_found,
				tab: 'web-assets',
				trend: trendOf('endpoints_found')
			});
		return list;
	});

	function pickCountry(code: string) {
		onTab('ips', code ? `country:${code}` : '');
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div
		class="grid {showGeo
			? 'lg:grid-cols-[minmax(0,1fr)_19rem] xl:grid-cols-[minmax(0,1fr)_22rem]'
			: ''}"
	>
		<div class="flex min-w-0 flex-col">
			<div class="flex flex-col gap-2 px-5 pt-5 pb-4">
				<h2 class="flex items-center gap-2.5 text-xl font-semibold tracking-tight sm:text-2xl">
					{#if scan.status === 'running'}
						<Spinner class="size-5 text-info" />
					{/if}
					{headline}
				</h2>
				{#if subline}
					<p class="text-sm text-muted-foreground">{subline}</p>
				{:else if !historyLoaded}
					<Skeleton class="h-4 w-72" />
				{/if}
				{#if (compared && (added > 0 || gone > 0)) || history.length > 1}
					<div class="mt-1 flex flex-wrap items-center gap-2">
						{#if compared && added > 0}
							<button
								type="button"
								class="inline-flex h-6 items-center gap-1 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60"
								onclick={() => onTab('web-assets', NEW_FILTER)}
								aria-label="View {added.toLocaleString()} new {nounPlural}"
							>
								<ArrowUpRight class="size-3.5 text-success" />
								<span class="font-medium tabular-nums">{added.toLocaleString()}</span>
								new
							</button>
						{/if}
						{#if compared && gone > 0}
							<span
								class="inline-flex h-6 items-center gap-1 rounded-md border border-dashed px-2 text-xs text-muted-foreground"
								title="Present in the previous scan, absent in this one"
							>
								<ArrowDownRight class="size-3.5" />
								<span class="font-medium tabular-nums">{gone.toLocaleString()}</span>
								not seen
							</span>
						{/if}
						{#if history.length > 1}
							<HistoryPopover {history} current={scan} {nounPlural} />
						{/if}
					</div>
				{/if}
			</div>

			<RunRibbon
				{scan}
				{run}
				{catalog}
				{activities}
				{commands}
				{now}
				{previousDuration}
				{scanId}
				{projectId}
				class="px-5 pb-5"
			/>

			<div class="mt-auto -ml-px grid grid-cols-2 sm:grid-cols-3">
				{#each kpis as k (k.key)}
					<button
						type="button"
						class="group flex min-w-0 cursor-pointer items-end justify-between gap-3 border-t border-l px-5 py-4 text-left transition-colors hover:bg-muted/40"
						onclick={() => onTab(k.tab, k.filter)}
					>
						<span class="flex min-w-0 flex-col gap-1.5">
							<span class="truncate text-xs text-muted-foreground group-hover:text-foreground">
								{k.label}
							</span>
							<span class="text-2xl leading-none font-semibold tracking-tight">
								{k.value == null ? '—' : k.value.toLocaleString()}
							</span>
							<span class="flex h-4 items-center gap-2 text-xs tabular-nums">
								{#if (k.added ?? 0) > 0 || (k.gone ?? 0) > 0}
									{#if (k.added ?? 0) > 0}
										<span class="inline-flex items-center text-success">
											<ArrowUpRight class="size-3" />{k.added}
										</span>
									{/if}
									{#if (k.gone ?? 0) > 0}
										<span class="inline-flex items-center text-muted-foreground">
											<ArrowDownRight class="size-3" />{k.gone}
										</span>
									{/if}
								{:else if k.diff != null}
									<span class="inline-flex items-center text-muted-foreground">
										{#if k.diff > 0}<ArrowUpRight class="size-3" />{:else}<ArrowDownRight
												class="size-3"
											/>{/if}
										{Math.abs(k.diff).toLocaleString()}
									</span>
								{:else if k.hint}
									<span class="truncate text-muted-foreground">{k.hint}</span>
								{/if}
							</span>
						</span>
						{#if k.trend}
							<ScanTrendSparkline
								values={k.trend}
								label={k.label}
								class="hidden h-9 w-20 shrink-0 xl:flex"
							/>
						{/if}
					</button>
				{/each}
			</div>
		</div>

		{#if showGeo}
			<GeoPanel
				{geography}
				total={geoTotal}
				{live}
				ready={geoReady}
				class="border-t lg:border-t-0 lg:border-l"
				onPick={pickCountry}
			/>
		{/if}
	</div>
</Card.Root>
