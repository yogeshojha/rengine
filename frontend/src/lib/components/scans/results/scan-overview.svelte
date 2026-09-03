<script lang="ts">
	import DonutChart from './charts/donut-chart.svelte';
	import HorizontalBarChart from './charts/horizontal-bar-chart.svelte';
	import TechStackCard from './overview/tech-stack-card.svelte';
	import { Button } from '$lib/components/ui/button';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ChartCard from './overview/chart-card.svelte';
	import SummaryCard from './overview/summary-card.svelte';
	import InsightsCard from './overview/insights-card.svelte';
	import RunCard from './overview/run-card.svelte';
	import PreviousRuns from './overview/previous-runs.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { isLiveStatus } from '$lib/utilities/scan-status';
	import { targetAssetNoun, TargetType } from '$lib/types/target';
	import type { ScanActivityRead, ScanRead } from '$lib/types/scan';
	import type { StatusClass } from '$lib/utilities/scan-correlation';
	import type {
		SubdomainInsights,
		InsightBucket,
		InsightTally
	} from '$lib/utilities/scan-insights';
	import type { DonutSlice } from './charts/donut-chart.svelte';
	import type { Bar } from './charts/horizontal-bar-chart.svelte';

	interface Props {
		scan: ScanRead;
		scanId: string;
		projectId: string;
		activities: ScanActivityRead[];
		history: ScanRead[];
		historyLoaded: boolean;
		previous: ScanRead | null;
		previousDuration: number | null;
		now: number;
		active?: boolean;
		onFilter: (search: string) => void;
		onTab: (tab: string, filter?: string) => void;
		onRescan: () => void;
	}

	let {
		scan,
		scanId,
		projectId,
		activities,
		history,
		historyLoaded,
		previous,
		previousDuration,
		now,
		active = true,
		onFilter,
		onTab,
		onRescan
	}: Props = $props();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	const CHART_FILL: Record<StatusClass, string> = {
		success: 'var(--chart-2)',
		info: 'var(--chart-1)',
		warning: 'var(--chart-4)',
		destructive: 'var(--destructive)',
		muted: 'var(--muted-foreground)'
	};
	const STATUS_FILTER: Record<string, string> = {
		live: 'status:2xx',
		redirect: 'status:3xx',
		auth: 'is:auth',
		error: 'status:4xx status:5xx',
		none: 'status:none'
	};
	const CERT_FILTER: Record<string, string> = {
		expired: 'cert:expired',
		d7: 'cert:expiring',
		d30: 'cert:expiring',
		d90: 'cert:valid',
		ok: 'cert:valid'
	};
	const ASSESSING_STAGE = 'http_probe';
	const SEED_SOURCE = 'target';
	const MAX_CHARTS = 4;
	const MIN_SLICES = 2;

	let insights = $state<SubdomainInsights | null>(null);
	let loading = $state(true);
	let errored = $state(false);

	let live = $derived(isLiveStatus(scan.status));
	let run = $derived(live ? liveScans.runFor(scan.id) : undefined);
	let catalog = $derived(engineCatalogStore.stages);
	let type = $derived(scan.execution_config.target_type);
	let nounPlural = $derived(targetAssetNoun(type));
	let nounTitle = $derived(nounPlural.charAt(0).toUpperCase() + nounPlural.slice(1));
	let isDomain = $derived(type === TargetType.DOMAIN);
	let assessed = $derived(
		activities.some((a) => a.name === ASSESSING_STAGE && a.status === 'success')
	);
	let revision = $derived(
		[
			scan.status,
			scan.subdomains_found,
			scan.ips_found,
			scan.http_assets_found,
			scan.open_ports_found
		].join(':')
	);

	function loadInsights() {
		const id = scanId;
		const pid = projectId;
		if (!id || !pid) return;
		if (!insights) loading = true;
		errored = false;
		subdomainsApi
			.insights(pid, id)
			.then((d) => {
				insights = d;
				errored = false;
			})
			.catch(() => {
				if (!insights) errored = true;
			})
			.finally(() => (loading = false));
	}

	$effect(() => {
		void revision;
		if (!seen) return;
		loadInsights();
	});

	$effect(() => {
		if (!engineCatalogStore.hasFetched) engineCatalogStore.fetch();
	});

	function toDonut(buckets: InsightBucket[], filters: Record<string, string>): DonutSlice[] {
		return buckets.map((b) => ({
			key: b.key,
			label: b.label,
			count: b.count,
			color: CHART_FILL[b.klass],
			filter: filters[b.key]
		}));
	}
	const sum = (xs: { count: number }[]) => xs.reduce((n, d) => n + d.count, 0);
	const toBars = (xs: InsightTally[]): Bar[] => xs.map((t) => ({ label: t.name, count: t.count }));

	interface ChartSpec {
		key: string;
		title: string;
		description: string;
		footer: string;
		action?: { label: string; filter: string };
		donut?: { slices: DonutSlice[]; center: string };
		bars?: { bars: Bar[]; valueLabel: string; labelWidth: number; filterKey?: string };
		tech?: true;
	}

	let resolved = $derived(insights?.surface.find((s) => s.key === 'resolved')?.value ?? null);
	let liveHosts = $derived(insights?.surface.find((s) => s.key === 'live')?.value ?? 0);
	let webHosts = $derived(insights?.surface.find((s) => s.key === 'web')?.value ?? 0);
	let charts = $derived.by<ChartSpec[]>(() => {
		if (!insights) return [];
		const status = toDonut(insights.status_reframe, STATUS_FILTER);
		const certs = toDonut(insights.cert_buckets, CERT_FILTER);
		const sources = insights.sources.filter((s) => s.name !== SEED_SOURCE);
		const broken = insights.status_reframe.find((b) => b.key === 'error')?.count ?? 0;
		const expiring = insights.cert_buckets
			.filter((b) => b.key === 'expired' || b.key === 'd7' || b.key === 'd30')
			.reduce((n, b) => n + b.count, 0);
		const sensitive = insights.attention.find((a) => a.key === 'sensitive')?.count ?? 0;
		const webStatus = status.filter((d) => d.key !== 'none');
		const all: (ChartSpec | null)[] = [
			webStatus.length >= MIN_SLICES
				? {
						key: 'http',
						title: 'HTTP status',
						description: 'Hosts by response class',
						footer: `${liveHosts.toLocaleString()} of ${webHosts.toLocaleString()} web hosts respond with 2xx`,
						action:
							broken > 0
								? {
										label: `${broken.toLocaleString()} returning errors`,
										filter: STATUS_FILTER.error
									}
								: undefined,
						donut: { slices: webStatus, center: 'web hosts' }
					}
				: null,
			insights.top_tech.length
				? { key: 'tech', title: '', description: '', footer: '', tech: true }
				: null,
			certs.length >= MIN_SLICES
				? {
						key: 'certs',
						title: 'Certificate expiry',
						description: 'TLS certificates by time remaining',
						footer:
							expiring > 0
								? `${expiring.toLocaleString()} ${expiring === 1 ? 'certificate expires' : 'certificates expire'} within 30 days`
								: 'No certificates expire within 30 days',
						action:
							expiring > 0 ? { label: 'View hosts', filter: CERT_FILTER.expiring } : undefined,
						donut: { slices: certs, center: 'certificates' }
					}
				: null,
			insights.services.length
				? {
						key: 'services',
						title: 'Exposed services',
						description: 'Open ports by detected service',
						footer:
							sensitive > 0
								? `${sensitive.toLocaleString()} hosts expose sensitive services`
								: 'No sensitive services exposed',
						action: sensitive > 0 ? { label: 'View hosts', filter: 'sensitive:true' } : undefined,
						bars: {
							bars: toBars(insights.services),
							valueLabel: 'Ports',
							labelWidth: 96,
							filterKey: 'service'
						}
					}
				: null,
			isDomain && sources.length
				? {
						key: 'sources',
						title: 'Discovery sources',
						description: `${nounTitle} reported by each source`,
						footer: sources[0]
							? `${sources[0].name} reported the most, ${sources[0].count.toLocaleString()} of ${scan.subdomains_found.toLocaleString()}`
							: '',
						bars: {
							bars: toBars(sources),
							valueLabel: nounTitle,
							labelWidth: 96,
							filterKey: 'source'
						}
					}
				: null,
			insights.top_asn.length
				? {
						key: 'asn',
						title: 'Hosting networks',
						description: 'IP addresses by network operator',
						footer: `${insights.top_asn.length} networks host this surface`,
						bars: {
							bars: toBars(insights.top_asn),
							valueLabel: 'IP addresses',
							labelWidth: 132
						}
					}
				: null
		];
		return all.filter((c): c is ChartSpec => c !== null).slice(0, MAX_CHARTS);
	});
</script>

<div class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
	<div class="flex min-w-0 flex-col gap-6">
		<SummaryCard
			{scan}
			{previous}
			{historyLoaded}
			{resolved}
			{run}
			{catalog}
			{activities}
			{previousDuration}
			{now}
			{onTab}
		/>

		<InsightsCard
			{scan}
			attention={insights?.attention ?? []}
			clusters={insights?.clusters ?? []}
			{assessed}
			{live}
			loading={loading && !insights}
			errored={errored && !insights}
			{onFilter}
			{onRescan}
			onRetry={loadInsights}
		/>

		{#if charts.length && insights}
			<div class="grid grid-cols-1 gap-6 md:grid-cols-2">
				{#each charts as c, i (c.key)}
					{@const span = i === charts.length - 1 && charts.length % 2 === 1 ? 'md:col-span-2' : ''}
					{#if c.tech}
						<TechStackCard
							top={insights.top_tech}
							total={insights.tech_total}
							hosts={liveHosts}
							{scanId}
							{projectId}
							{onFilter}
							class={span}
						/>
					{:else}
						<ChartCard title={c.title} description={c.description} class={span}>
							{#if c.donut}
								<DonutChart
									slices={c.donut.slices}
									total={sum(c.donut.slices)}
									centerLabel={c.donut.center}
									onSelect={onFilter}
								/>
							{:else if c.bars}
								{@const bars = c.bars}
								<HorizontalBarChart
									bars={bars.bars}
									valueLabel={bars.valueLabel}
									labelWidth={bars.labelWidth}
									onSelect={bars.filterKey ? (n) => onFilter(`${bars.filterKey}:${n}`) : undefined}
								/>
							{/if}
							{#snippet footer()}
								<div class="leading-none text-muted-foreground">{c.footer}</div>
								{#if c.action}
									{@const action = c.action}
									<Button
										variant="link"
										size="sm"
										class="h-auto gap-1 px-0"
										onclick={() => onFilter(action.filter)}
									>
										{action.label}
										<ChevronRight class="size-3.5" />
									</Button>
								{/if}
							{/snippet}
						</ChartCard>
					{/if}
				{/each}
			</div>
		{/if}
	</div>

	<div class="flex min-w-0 flex-col gap-6">
		<RunCard {scan} {run} {catalog} {activities} {now} onPipeline={() => onTab('pipeline')} />
		<PreviousRuns {history} current={scan} loading={!historyLoaded} {nounPlural} />
	</div>
</div>
