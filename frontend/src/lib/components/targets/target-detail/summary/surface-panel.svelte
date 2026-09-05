<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Play from '@lucide/svelte/icons/play';
	import Radar from '@lucide/svelte/icons/radar';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';
	import SurfaceCell from './surface-cell.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { relativeTime, formatShortDate } from '$lib/utilities/dates';
	import { durationText, isLiveStatus } from '$lib/utilities/scan-status';
	import type { ScanStatus } from '$lib/types/scan';
	import type { TargetSummaryRead } from '$lib/types/target-summary';

	interface Props {
		summary: TargetSummaryRead | null;
		loading: boolean;
		onScan: () => void;
		onTab: (tab: string) => void;
	}

	let { summary, loading, onScan, onTab }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	let latest = $derived(summary?.latest_scan ?? null);
	let live = $derived(latest ? isLiveStatus(latest.status as ScanStatus) : false);
	let scanned = $derived((summary?.scans_total ?? 0) > 0);
	let surface = $derived(summary?.surface ?? []);
	let web = $derived(surface.find((m) => m.key === SurfaceDimension.WEB_ASSETS));
	let compared = $derived(web?.added != null);
	let added = $derived(web?.added ?? 0);
	let gone = $derived(web?.gone ?? 0);

	let headline = $derived.by(() => {
		if (!scanned) return 'Not scanned yet';
		if (live) return 'Scan in progress';
		if (!latest) return 'Not scanned yet';
		if (latest.status === 'failed') return 'Last scan failed';
		if (latest.status === 'cancelled') return 'Last scan was cancelled';
		if (!compared) return 'Baseline recorded';
		if (added > 0)
			return `${added.toLocaleString()} new ${added === 1 ? WEB.noun : WEB.nounPlural}`;
		return gone > 0 ? `No new ${WEB.nounPlural}` : 'No change since the previous scan';
	});

	let subline = $derived.by(() => {
		if (!scanned) return "Run a scan to map this target's attack surface.";
		if (!latest) return '';
		const started = relativeTime(latest.started_at ?? latest.created_at);
		if (live) return `${latest.engine_name} · started ${started}`;
		const parts = [`Last scanned ${started} by ${latest.engine_name}`];
		if (latest.duration_seconds != null) parts.push(durationText(latest.duration_seconds));
		if (latest.status === 'failed' && latest.error) parts.push(latest.error);
		else if (!compared && latest.status === 'completed')
			parts.push('later scans are compared against it');
		return parts.join(' · ');
	});

	let vulnNote = $derived.by(() => {
		const risk = summary?.risk;
		if (!risk || risk.total === 0) return undefined;
		const worst = risk.by_severity.find((s) => s.count > 0);
		return worst ? `${worst.count.toLocaleString()} ${worst.label.toLowerCase()}` : undefined;
	});
	let serviceNote = $derived(
		summary?.sensitive_services
			? `${summary.sensitive_services.toLocaleString()} sensitive`
			: undefined
	);
	const noteFor = (key: string) => {
		if (key === SurfaceDimension.VULNERABILITIES) return vulnNote;
		if (key === SurfaceDimension.SERVICES) return serviceNote;
		return undefined;
	};
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="flex flex-col gap-2 px-5 pt-5 pb-4">
		{#if loading && !summary}
			<Skeleton class="h-7 w-64" />
			<Skeleton class="h-4 w-96" />
		{:else}
			<h2 class="flex items-center gap-2.5 text-xl font-semibold tracking-tight sm:text-2xl">
				{#if live}
					<Spinner class="size-5 text-info" />
				{/if}
				{headline}
			</h2>
			<p class="text-sm text-muted-foreground">{subline}</p>
		{/if}

		{#if summary}
			<div class="mt-1 flex flex-wrap items-center gap-2">
				{#if compared && added > 0 && latest}
					<a
						href={ROUTES.scanTab(latest.id, WEB.tab, { [WEB.queryParam]: 'is:new' })}
						class="inline-flex h-6 items-center gap-1 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60"
					>
						<ArrowUpRight class="size-3.5 text-success" />
						<span class="font-medium tabular-nums">{added.toLocaleString()}</span>
						new
					</a>
				{/if}
				{#if compared && gone > 0}
					<Hint text="Present in the previous scan, absent in the latest one">
						{#snippet child(props)}
							<span
								{...props}
								class="inline-flex h-6 items-center gap-1 rounded-md border border-dashed px-2 text-xs text-muted-foreground"
							>
								<ArrowDownRight class="size-3.5" />
								<span class="font-medium tabular-nums">{gone.toLocaleString()}</span>
								not seen
							</span>
						{/snippet}
					</Hint>
				{/if}
				{#if summary.monitoring}
					{@const watch = summary.monitoring}
					<Hint
						text="Scheduled by {watch.name}{watch.next_run_at
							? ` · next run ${formatShortDate(watch.next_run_at)}`
							: ''}"
					>
						{#snippet child(props)}
							<a
								{...props}
								href={ROUTES.schedules}
								class="inline-flex h-6 items-center gap-1 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60"
							>
								<CalendarClock class="size-3.5" />
								{watch.cadence}
							</a>
						{/snippet}
					</Hint>
				{:else if scanned}
					<span
						class="inline-flex h-6 items-center gap-1 rounded-md border border-dashed px-2 text-xs text-muted-foreground"
					>
						<CalendarClock class="size-3.5" />
						Not scheduled
					</span>
				{/if}
				{#if summary.scans_failed > 0}
					<button
						type="button"
						class="inline-flex h-6 items-center gap-1 rounded-md border border-destructive/30 px-2 text-xs text-destructive transition-colors hover:bg-destructive/5"
						onclick={() => onTab('scans')}
					>
						<TriangleAlert class="size-3.5" />
						<span class="font-medium tabular-nums">{summary.scans_failed}</span>
						failed
					</button>
				{/if}
				{#if scanned}
					<button
						type="button"
						class="inline-flex h-6 items-center gap-1 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60"
						onclick={() => onTab('scans')}
					>
						<span class="font-medium tabular-nums">{summary.scans_total}</span>
						{summary.scans_total === 1 ? 'scan' : 'scans'}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	{#if loading && !summary}
		<div class="-ml-px grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
			{#each Array(5) as _, i (i)}
				<div class="flex flex-col gap-2 border-t border-l px-5 py-4">
					<Skeleton class="h-3 w-20" />
					<Skeleton class="h-7 w-16" />
					<Skeleton class="h-3 w-14" />
				</div>
			{/each}
		</div>
	{:else if scanned}
		<div class="-ml-px grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
			{#each surface as metric (metric.key)}
				<SurfaceCell {metric} note={noteFor(metric.key)} />
			{/each}
		</div>
	{:else}
		<div class="flex flex-col items-center gap-3 border-t px-5 py-10 text-center">
			<div class="flex size-12 items-center justify-center rounded-2xl bg-muted">
				<Radar class="size-6 text-muted-foreground/60" />
			</div>
			<p class="max-w-sm text-sm text-muted-foreground">
				Web assets, endpoints, services, addresses and findings appear here once a scan has run.
			</p>
			<Button class="gap-2" onclick={onScan}>
				<Play class="size-4" /> Start scan
			</Button>
		</div>
	{/if}
</Card.Root>
