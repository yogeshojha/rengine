<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';
	import Play from '@lucide/svelte/icons/play';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import ScanTrendSparkline from '$lib/components/scans/scan-trend-sparkline.svelte';
	import SectionHead from '../section-head.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension, surfaceSpec } from '$lib/config/surface';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { durationText, isLiveStatus } from '$lib/utilities/scan-status';
	import type { ScanRead, ScanStatus } from '$lib/types/scan';
	import type { SurfaceMetric, TargetSummaryRead } from '$lib/types/target-summary';

	interface Props {
		summary: TargetSummaryRead | null;
		loading: boolean;
		history: ScanRead[];
		onScan: () => void;
	}

	let { summary, loading, history, onScan }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const TREND_RUNS = 6;
	const TREND_COLUMN: Record<string, keyof ScanRead> = {
		[SurfaceDimension.WEB_ASSETS]: 'subdomains_found',
		[SurfaceDimension.ENDPOINTS]: 'endpoints_found',
		[SurfaceDimension.SERVICES]: 'open_ports_found',
		[SurfaceDimension.IPS]: 'ips_found',
		[SurfaceDimension.VULNERABILITIES]: 'vulnerabilities_found'
	};

	let latest = $derived(summary?.latest_scan ?? null);
	let live = $derived(latest ? isLiveStatus(latest.status as ScanStatus) : false);
	let scanned = $derived((summary?.scans_total ?? 0) > 0);
	let surface = $derived(summary?.surface ?? []);
	let observedAt = $derived.by(() => {
		const dates = surface.filter((m) => m.covered && m.observed_at).map((m) => m.observed_at!);
		return dates.length ? dates.sort().at(-1)! : null;
	});

	let completedRuns = $derived(
		history
			.filter((s) => s.status === 'completed')
			.sort(
				(a, b) =>
					new Date(a.started_at ?? a.created_at).getTime() -
					new Date(b.started_at ?? b.created_at).getTime()
			)
			.slice(-TREND_RUNS)
	);
	function trendFor(key: string): number[] | null {
		if (completedRuns.length < 2) return null;
		const column = TREND_COLUMN[key];
		if (!column) return null;
		const values = completedRuns.map((s) => Number(s[column] ?? 0));
		return values.some((v) => v > 0) ? values : null;
	}

	let count = $derived(observedAt ? `as observed ${formatShortDate(observedAt)}` : null);
	let status = $derived.by(() => {
		if (!latest) return null;
		if (live) return null;
		const when = relativeTime(latest.completed_at ?? latest.started_at ?? latest.created_at);
		const took = latest.duration_seconds != null ? durationText(latest.duration_seconds) : null;
		if (latest.status === 'cancelled')
			return {
				live: false,
				text: `Latest run was cancelled${took ? ` after ${took}` : ''}, figures are partial`
			};
		if (latest.status === 'failed')
			return {
				live: false,
				text: `Latest run failed ${when}${latest.error ? ` · ${latest.error}` : ''}`
			};
		if (latest.is_first_scan || latest.prev_subdomains_found == null)
			return { live: false, text: 'Baseline run, later runs are compared against it' };
		return { live: false, text: `Compared with the previous run · ${latest.engine_name} ${when}` };
	});

	type Note = { text: string; tone?: 'up' | 'down' | 'warn' | 'bad' };
	function noteFor(m: SurfaceMetric): Note | null {
		if (!m.covered) return { text: 'Not scanned' };
		if (m.key === SurfaceDimension.VULNERABILITIES && summary?.risk.total) {
			const worst = summary.risk.by_severity.find((s) => s.count > 0);
			if (worst)
				return {
					text: `${worst.count.toLocaleString()} ${worst.label.toLowerCase()}`,
					tone: worst.severity === 'critical' || worst.severity === 'high' ? 'bad' : 'warn'
				};
		}
		if (m.key === SurfaceDimension.SERVICES && summary?.sensitive_services)
			return { text: `${summary.sensitive_services.toLocaleString()} sensitive`, tone: 'warn' };
		if (m.scan_status === 'running') return { text: 'so far' };
		if (!m.current && m.observed_at) return { text: `as of ${formatShortDate(m.observed_at)}` };
		if (m.added != null) {
			if (m.added > 0) return { text: `${m.added.toLocaleString()} new`, tone: 'up' };
			if (m.gone) return { text: `${m.gone.toLocaleString()} gone`, tone: 'down' };
			return { text: 'No change' };
		}
		if (m.delta)
			return { text: Math.abs(m.delta).toLocaleString(), tone: m.delta > 0 ? 'up' : 'down' };
		if (m.previous == null) return (summary?.scans_total ?? 0) <= 1 ? { text: 'first scan' } : null;
		return { text: 'No change' };
	}
	const hrefFor = (m: SurfaceMetric) => {
		const spec = surfaceSpec(m.key);
		return m.scan_id && spec ? ROUTES.scanTab(m.scan_id, spec.tab) : null;
	};
	const TONE = {
		up: 'text-success',
		down: 'text-muted-foreground',
		warn: 'text-warning',
		bad: 'text-destructive'
	};
</script>

<section class="flex flex-col gap-3 pb-5">
	<SectionHead title="Surface" count={scanned && !live ? count : live ? 'updating' : null}>
		{#if status}
			<span>{status.text}</span>
		{/if}
	</SectionHead>

	{#if loading && !summary}
		<div class="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
			{#each Array(5) as _, i (i)}
				<Skeleton class="h-[66px] rounded-[10px]" />
			{/each}
		</div>
	{:else if scanned}
		<div class="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
			{#each surface as m (m.key)}
				{@const spec = surfaceSpec(m.key)}
				{@const note = noteFor(m)}
				{@const href = hrefFor(m)}
				{@const trend = trendFor(m.key)}
				{@const Icon = spec?.icon}
				<Hint
					text={m.covered
						? `Open ${spec?.label ?? m.label} in the scan that observed it`
						: `No scan of this target has run ${spec?.label ?? m.label} yet`}
				>
					{#snippet child(props)}
						<svelte:element
							this={href ? 'a' : 'div'}
							{...props}
							{href}
							class="grid min-h-[66px] grid-cols-[minmax(0,1fr)_auto] items-end gap-x-2 gap-y-0.5 rounded-[10px] border px-3 py-2.5 transition-colors {href
								? 'hover:border-primary/40 hover:bg-accent/40'
								: ''} {m.covered ? '' : 'border-dashed'}"
						>
							<span class="col-span-2 flex items-center gap-1.5 text-xs text-muted-foreground">
								{#if Icon}<Icon class="size-3.5" />{/if}
								{m.label}
							</span>
							<span
								class="text-[22px] leading-none font-semibold tracking-tight tabular-nums {m.covered
									? ''
									: 'font-medium text-muted-foreground'}"
							>
								{m.value == null ? '—' : m.value.toLocaleString()}
							</span>
							{#if trend}
								<ScanTrendSparkline
									values={trend}
									label={m.label}
									class="hidden h-6 w-16 shrink-0 xl:flex"
								/>
							{:else if note}
								<span
									class="flex items-center pb-px text-xs {note.tone
										? TONE[note.tone]
										: 'text-muted-foreground'}"
								>
									{#if note.tone === 'up'}<ArrowUpRight class="size-3" />{/if}
									{#if note.tone === 'down'}<ArrowDownRight class="size-3" />{/if}
									{note.text}
								</span>
							{/if}
						</svelte:element>
					{/snippet}
				</Hint>
			{/each}
		</div>
	{:else}
		<div
			class="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-dashed px-4 py-3"
		>
			<p class="text-sm text-muted-foreground">
				No scans yet. {WEB.label}, endpoints, services, addresses and findings appear here after the
				first run.
			</p>
			<Button size="sm" class="gap-1.5" onclick={onScan}>
				<Play class="size-3.5" /> Start scan
			</Button>
		</div>
	{/if}
</section>
