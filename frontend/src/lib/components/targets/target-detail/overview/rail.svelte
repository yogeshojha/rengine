<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import CopyButton from '$lib/components/copy-button.svelte';
	import TechIcon from '$lib/components/scans/results/tech-icon.svelte';
	import CountryFlag from '$lib/components/scans/results/country-flag.svelte';
	import GeoPanel from '$lib/components/scans/results/overview/geo-panel.svelte';
	import type { InsightTally } from '$lib/utilities/scan-insights';
	import { ROUTES } from '$lib/config/routes';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import {
		durationText,
		elapsedSeconds,
		formatSeconds,
		isLiveStatus,
		SCAN_STATUS_LABEL
	} from '$lib/utilities/scan-status';
	import type { ScanStatus } from '$lib/types/scan';
	import type { TargetSummaryRead } from '$lib/types/target-summary';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';
	import type { RailGroup, Tone } from './derive';

	interface Props {
		groups: RailGroup[];
		summary: TargetSummaryRead | null;
		loading: boolean;
		enrichedAt: string | null;
		run: LiveRun | undefined;
		now: number;
		geography: InsightTally[];
		geoTotal: number;
		geoReady: boolean;
		live: boolean;
		onPickCountry: (code: string) => void;
		onTab: (tab: string) => void;
		onRefresh: () => void;
	}

	let {
		groups,
		summary,
		loading,
		enrichedAt,
		run,
		now,
		geography,
		geoTotal,
		geoReady,
		live: scanLive,
		onTab,
		onRefresh,
		onPickCountry
	}: Props = $props();

	const TONE: Record<Tone, string> = {
		neutral: '',
		good: '',
		warn: 'text-warning',
		bad: 'text-destructive'
	};
	const DOT: Record<ScanStatus, string> = {
		completed: 'bg-success',
		cancelled: 'bg-warning',
		failed: 'bg-destructive',
		running: 'bg-info shadow-[0_0_0_3px_color-mix(in_oklch,var(--info)_18%,transparent)]',
		pending: 'bg-muted-foreground/50'
	};

	let latest = $derived(summary?.latest_scan ?? null);
	let live = $derived(latest ? isLiveStatus(latest.status as ScanStatus) : false);
	let scanLine = $derived.by(() => {
		if (!latest) return null;
		if (live) return latest.engine_name;
		const parts = [latest.engine_name, formatShortDate(latest.started_at ?? latest.created_at)];
		if (latest.duration_seconds != null) parts.push(durationText(latest.duration_seconds));
		return parts.join(' · ');
	});
	let liveLine = $derived.by(() => {
		if (!latest || !live) return null;
		const parts: string[] = [];
		if (run?.stage?.title) parts.push(run.stage.title);
		const e = elapsedSeconds(latest, now);
		if (e != null) parts.push(`${formatSeconds(e)} elapsed`);
		return parts.join(' · ');
	});
</script>

<aside class="flex flex-col divide-y">
	{#if geography.length || (!geoReady && summary?.surface.some((m) => m.key === 'ips' && m.covered))}
		<GeoPanel
			{geography}
			total={geoTotal}
			live={scanLive}
			ready={geoReady}
			class="p-0 pb-4"
			onPick={onPickCountry}
		/>
	{/if}
	<div class="flex flex-col gap-1.5 pb-4">
		<h4 class="mb-1 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase">
			Scan
		</h4>
		{#if loading && !summary}
			<Skeleton class="h-4 w-40" />
			<Skeleton class="h-4 w-28" />
		{:else if latest}
			<div class="flex items-start gap-2 text-[13px]">
				<span class="flex h-5 shrink-0 items-center">
					<span class="size-2 rounded-full {DOT[latest.status]}" aria-hidden="true"></span>
				</span>
				<span class="flex min-w-0 flex-col">
					<span class="leading-5">
						<span class="font-medium">{SCAN_STATUS_LABEL[latest.status]}</span>
						<span class="text-muted-foreground"> · {scanLine}</span>
					</span>
					{#if liveLine}
						<span class="text-xs text-muted-foreground">{liveLine}</span>
					{/if}
				</span>
			</div>
			<div class="grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2 text-[13px]">
				<span class="pt-px text-xs text-muted-foreground">Runs</span>
				<span class="tabular-nums">
					{summary!.scans_total}{#if summary!.first_scan_at}<span class="text-muted-foreground">
							· first {formatShortDate(summary!.first_scan_at)}</span
						>{/if}
				</span>
			</div>
		{:else}
			<div class="flex items-center gap-2 text-[13px]">
				<span class="size-2 shrink-0 rounded-full {DOT.pending}" aria-hidden="true"></span>
				<span class="text-muted-foreground">Not scanned yet</span>
			</div>
		{/if}
		{#if summary}
			<div class="grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2 text-[13px]">
				<span class="pt-px text-xs text-muted-foreground">Monitoring</span>
				{#if summary.monitoring}
					<a href={ROUTES.schedules} class="hover:underline">
						{summary.monitoring.cadence}
						{#if summary.monitoring.next_run_at}
							<span class="block text-xs text-muted-foreground"
								>next {formatShortDate(summary.monitoring.next_run_at)}</span
							>
						{/if}
					</a>
				{:else}
					<span>
						Not scheduled
						<a href={ROUTES.schedules} class="block text-xs font-medium text-primary"
							>Set a schedule</a
						>
					</span>
				{/if}
			</div>
		{/if}
	</div>

	{#each groups as g (g.key)}
		<div class="flex flex-col gap-1.5 py-4">
			<h4
				class="mb-1 flex items-baseline justify-between gap-3 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase"
			>
				{g.title}
				{#if g.pending}
					<span
						class="flex items-center gap-1.5 text-xs font-medium tracking-normal normal-case text-info"
						><Spinner class="size-3" /> Collecting</span
					>
				{:else if g.link}
					<button
						type="button"
						class="text-xs font-medium tracking-normal normal-case text-primary hover:underline"
						onclick={() => onTab(g.link!.tab)}
					>
						{g.link.label}
					</button>
				{/if}
			</h4>
			{#if g.note}
				<div class="text-[13px] {TONE[g.note.tone]}">
					{g.note.text}
					{#if g.note.detail}
						<span class="block text-xs text-muted-foreground wrap-anywhere">{g.note.detail}</span>
					{/if}
				</div>
			{/if}
			{#if loading && !g.rows.length && !g.note}
				<Skeleton class="h-4 w-48" />
				<Skeleton class="h-4 w-36" />
			{/if}
			{#each g.rows as row (row.key)}
				<div
					class="group/row grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2 text-[13px] leading-[1.4]"
				>
					<span class="pt-px text-xs text-muted-foreground">{row.label}</span>
					<span class="flex min-w-0 flex-col wrap-anywhere {TONE[row.tone ?? 'neutral']}">
						<span class="flex min-w-0 items-center gap-1.5">
							{#if row.brand}
								<TechIcon name={row.brand} class="size-4 rounded-[4px]" />
							{/if}
							{#if row.flag}
								<CountryFlag code={row.flag} showCode={false} />
							{/if}
							<span class="min-w-0 {row.mono ? 'font-mono text-[12.5px]' : ''}">{row.value}</span>
							{#if row.copy}
								<span
									class="flex h-4 shrink-0 items-center opacity-100 transition-opacity sm:opacity-0 sm:group-hover/row:opacity-100"
								>
									<CopyButton value={row.copy} class="size-5" />
								</span>
							{/if}
						</span>
						{#if row.sub}
							<span class="text-xs text-muted-foreground">{row.sub}</span>
						{/if}
					</span>
				</div>
			{/each}
		</div>
	{/each}

	<div class="flex gap-2.5 pt-3 text-xs text-muted-foreground">
		<span>{enrichedAt ? `Enriched ${relativeTime(enrichedAt)}` : 'Not enriched'}</span>
		<button type="button" class="font-medium text-primary hover:underline" onclick={onRefresh}
			>Refresh</button
		>
	</div>
</aside>
