<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import Link2 from '@lucide/svelte/icons/link-2';
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import RankBarChart from './rank-bar-chart.svelte';
	import CategoryDonut from './category-donut.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import type { ScanRead } from '$lib/types/scan';
	import type { StatusClass } from '$lib/utilities/scan-correlation';
	import type { SubdomainInsights, InsightBucket } from '$lib/utilities/scan-insights';

	interface Props {
		scan: ScanRead;
		scanId: string;
		projectId: string;
		active?: boolean;
		onFilter: (search: string) => void;
	}

	let { scan, scanId, projectId, active = true, onFilter }: Props = $props();

	let seen = $state(false);
	$effect(() => {
		if (active) seen = true;
	});

	const STATUS_VAR: Record<StatusClass, string> = {
		success: 'var(--chart-1)',
		info: 'var(--chart-2)',
		warning: 'var(--chart-4)',
		destructive: 'var(--destructive)',
		muted: 'var(--muted-foreground)'
	};

	let insights = $state<SubdomainInsights | null>(null);
	let loading = $state(true);
	let errored = $state(false);

	function loadInsights() {
		const id = scanId;
		const pid = projectId;
		if (!id || !pid) return;
		loading = true;
		errored = false;
		subdomainsApi
			.insights(pid, id)
			.then((d) => {
				insights = d;
				errored = false;
			})
			.catch(() => {
				insights = null;
				errored = true;
			})
			.finally(() => (loading = false));
	}

	$effect(() => {
		void scanId;
		void projectId;
		if (!seen) return;
		loadInsights();
	});

	let delta = $derived(
		scan && !scan.is_first_scan && ((scan.new_subdomains ?? 0) || (scan.gone_subdomains ?? 0))
			? { added: scan.new_subdomains ?? 0, removed: scan.gone_subdomains ?? 0 }
			: null
	);

	function toDonut(buckets: InsightBucket[]) {
		return buckets.map((b) => ({
			key: b.key,
			label: b.label,
			count: b.count,
			color: STATUS_VAR[b.klass]
		}));
	}
	let statusDonut = $derived(insights ? toDonut(insights.status_reframe) : []);
	let certDonut = $derived(insights ? toDonut(insights.cert_buckets) : []);
	let statusTotal = $derived(statusDonut.reduce((n, d) => n + d.count, 0));
	let certTotal = $derived(certDonut.reduce((n, d) => n + d.count, 0));
	let attention = $derived(insights?.attention ?? []);
	let surface = $derived(insights?.surface ?? []);
	let clusters = $derived(insights?.clusters ?? []);
</script>

<div class="flex flex-col gap-4">
	<div class="grid gap-4 lg:grid-cols-3">
		<Card.Root class="lg:col-span-2">
			<Card.Header class="pb-2">
				<Card.Title class="text-sm">What changed since the last scan</Card.Title>
			</Card.Header>
			<Card.Content>
				{#if scan.is_first_scan}
					<p class="text-xs text-muted-foreground">
						Baseline scan — future scans will diff new and retired assets against this one.
					</p>
				{:else if delta}
					<div class="flex flex-wrap items-center gap-x-6 gap-y-2">
						<span class="flex items-center gap-1.5 text-sm text-success">
							<ArrowUpRight class="size-4" />
							<span class="font-semibold tabular-nums">{delta.added}</span> new subdomains
						</span>
						<span class="flex items-center gap-1.5 text-sm text-muted-foreground">
							<ArrowDownRight class="size-4" />
							<span class="font-semibold tabular-nums">{delta.removed}</span> retired
						</span>
						<span class="text-xs text-muted-foreground">vs previous scan of this target</span>
					</div>
				{:else}
					<p class="text-xs text-muted-foreground">
						No change in the subdomain surface since the previous scan.
					</p>
				{/if}
			</Card.Content>
		</Card.Root>

		<Card.Root
			class={errored
				? 'border-destructive/30'
				: !insights
					? ''
					: attention.length
						? 'border-warning/30'
						: 'border-success/30'}
		>
			<Card.Header class="pb-2">
				<Card.Title class="flex items-center gap-1.5 text-sm">
					{#if loading || !insights}
						Needs attention
					{:else if errored}
						<TriangleAlert class="size-4 text-destructive" /> Couldn't load insights
					{:else if attention.length}
						<TriangleAlert class="size-4 text-warning" /> Needs attention
					{:else}
						<CircleCheck class="size-4 text-success" /> Looking clean
					{/if}
				</Card.Title>
			</Card.Header>
			<Card.Content>
				{#if loading}
					<Skeleton class="h-6 w-full" />
				{:else if errored}
					<button type="button" class="text-xs text-info hover:underline" onclick={loadInsights}>
						Retry
					</button>
				{:else if attention.length}
					<div class="flex flex-wrap gap-1.5">
						{#each attention as a (a.key)}
							<button type="button" onclick={() => onFilter(a.filter)}>
								<Badge variant={a.tone} class="cursor-pointer font-normal"
									>{a.count} {a.label}</Badge
								>
							</button>
						{/each}
					</div>
				{:else}
					<p class="text-xs text-muted-foreground">
						No expired certs, exposed services, or unprotected live hosts detected.
					</p>
				{/if}
			</Card.Content>
		</Card.Root>
	</div>

	{#if loading && !insights}
		<Skeleton class="h-20 w-full" />
		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			<Skeleton class="h-48 w-full" />
			<Skeleton class="h-48 w-full" />
			<Skeleton class="h-48 w-full" />
		</div>
	{:else if errored && !insights}
		<div
			class="flex flex-col items-center gap-2 rounded-lg border border-dashed py-12 text-sm text-muted-foreground"
		>
			<TriangleAlert class="size-5 text-destructive" />
			Couldn't load scan insights.
			<button type="button" class="text-xs text-info hover:underline" onclick={loadInsights}>
				Retry
			</button>
		</div>
	{:else if insights}
		<div class="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-9">
			{#each surface as stat (stat.key)}
				{#if stat.filter}
					<button
						type="button"
						class="cursor-pointer rounded-lg border bg-card/40 p-2.5 text-left hover:border-foreground/30"
						onclick={() => onFilter(stat.filter)}
					>
						<div class="text-lg font-semibold tabular-nums">{stat.value.toLocaleString()}</div>
						<div class="text-[11px] text-muted-foreground">{stat.label}</div>
					</button>
				{:else}
					<div class="rounded-lg border bg-card/40 p-2.5">
						<div class="text-lg font-semibold tabular-nums">{stat.value.toLocaleString()}</div>
						<div class="text-[11px] text-muted-foreground">{stat.label}</div>
					</div>
				{/if}
			{/each}
		</div>

		<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
			{#if statusDonut.length}
				<Card.Root>
					<Card.Header class="pb-2"
						><Card.Title class="text-sm">HTTP status</Card.Title></Card.Header
					>
					<Card.Content
						><CategoryDonut
							data={statusDonut}
							total={statusTotal}
							centerLabel="hosts"
						/></Card.Content
					>
				</Card.Root>
			{/if}

			{#if certTotal > 0}
				<Card.Root>
					<Card.Header class="pb-2"
						><Card.Title class="text-sm">Certificate expiry</Card.Title></Card.Header
					>
					<Card.Content
						><CategoryDonut data={certDonut} total={certTotal} centerLabel="certs" /></Card.Content
					>
				</Card.Root>
			{/if}

			{#if insights.top_tech.length}
				<Card.Root>
					<Card.Header class="pb-2"
						><Card.Title class="text-sm">Top technologies</Card.Title></Card.Header
					>
					<Card.Content
						><RankBarChart
							data={insights.top_tech}
							color="var(--chart-1)"
							label="Hosts"
						/></Card.Content
					>
				</Card.Root>
			{/if}

			{#if insights.top_asn.length}
				<Card.Root>
					<Card.Header class="pb-2"
						><Card.Title class="text-sm">Top networks</Card.Title></Card.Header
					>
					<Card.Content
						><RankBarChart
							data={insights.top_asn}
							color="var(--chart-3)"
							label="IPs"
						/></Card.Content
					>
				</Card.Root>
			{/if}

			{#if insights.services.length}
				<Card.Root>
					<Card.Header class="pb-2"><Card.Title class="text-sm">Services</Card.Title></Card.Header>
					<Card.Content
						><RankBarChart
							data={insights.services}
							color="var(--chart-4)"
							label="Ports"
						/></Card.Content
					>
				</Card.Root>
			{/if}

			{#if clusters.length}
				<Card.Root>
					<Card.Header class="pb-2">
						<Card.Title class="flex items-center gap-1.5 text-sm">
							<Link2 class="size-4 text-muted-foreground" /> Correlation clusters
						</Card.Title>
					</Card.Header>
					<Card.Content class="flex flex-col gap-1">
						{#each clusters as c (c.kind + c.value)}
							<div class="flex items-center gap-2 rounded-md px-1.5 py-1 text-xs">
								<Badge variant="secondary" class="rounded-sm px-1 font-mono font-normal"
									>{c.count}</Badge
								>
								<span class="truncate text-muted-foreground">hosts {c.reason}</span>
							</div>
						{/each}
					</Card.Content>
				</Card.Root>
			{/if}
		</div>
	{/if}
</div>
