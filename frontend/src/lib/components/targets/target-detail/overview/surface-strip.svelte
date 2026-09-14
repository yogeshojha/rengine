<script lang="ts">
	import Play from '@lucide/svelte/icons/play';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE_ORDER, SurfaceDimension, surfaceSpec } from '$lib/config/surface';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { isLiveStatus, SCAN_STATUS_DOT, SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import type { ScanRead, ScanStatus } from '$lib/types/scan';
	import type { SurfaceMetric, TargetSummaryRead } from '$lib/types/target-summary';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';

	interface Props {
		targetId: string;
		summary: TargetSummaryRead | null;
		loading: boolean;
		history: ScanRead[];
		run: LiveRun | undefined;
		onScan: () => void;
	}

	let { targetId, summary, loading, history, run, onScan }: Props = $props();

	const TREND_RUNS = 12;
	const W = 120;
	const H = 22;

	interface Tile {
		key: string;
		label: string;
		value: string;
		sub: string | null;
		tone: 'muted' | 'up' | 'down' | 'warn' | 'bad';
		bars: number[];
		href: string | null;
		hint: string;
		dot?: string;
		meta?: string;
	}

	let latest = $derived(summary?.latest_scan ?? null);
	let live = $derived(!!latest && isLiveStatus(latest.status as ScanStatus));
	let scanned = $derived((summary?.scans_total ?? 0) > 0);

	let completedRuns = $derived(
		history
			.filter((s) => s.status === 'completed' && s.scope !== 'focused')
			.sort(
				(a, b) =>
					new Date(a.started_at ?? a.created_at).getTime() -
					new Date(b.started_at ?? b.created_at).getTime()
			)
			.slice(-TREND_RUNS)
	);
	function trendFor(key: SurfaceDimension): number[] {
		if (completedRuns.length < 2) return [];
		const column = surfaceSpec(key)?.countColumns[0];
		if (!column) return [];
		const values = completedRuns.map((s) => Number(s[column] ?? 0));
		return values.some((v) => v > 0) ? values : [];
	}

	function noteFor(m: SurfaceMetric): { text: string; tone: Tile['tone'] } {
		if (!m.covered) return { text: 'Not scanned', tone: 'muted' };
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
		if (m.scan_status === 'running') return { text: 'so far', tone: 'muted' };
		if (!m.current && m.observed_at)
			return { text: `as of ${formatShortDate(m.observed_at)}`, tone: 'muted' };
		if (m.added != null) {
			if (m.added > 0) return { text: `▲ ${m.added.toLocaleString()}`, tone: 'up' };
			if (m.gone) return { text: `▼ ${m.gone.toLocaleString()}`, tone: 'down' };
			return { text: 'No change', tone: 'muted' };
		}
		if (m.delta)
			return {
				text: `${m.delta > 0 ? '▲' : '▼'} ${Math.abs(m.delta).toLocaleString()}`,
				tone: m.delta > 0 ? 'up' : 'down'
			};
		if (m.previous == null) return { text: 'first scan', tone: 'muted' };
		return { text: 'No change', tone: 'muted' };
	}

	let tiles = $derived.by<Tile[]>(() => {
		if (!summary) return [];
		const out: Tile[] = [];
		const when = latest
			? relativeTime(latest.completed_at ?? latest.started_at ?? latest.created_at)
			: null;
		out.push({
			key: 'runs',
			label: 'Runs',
			value: summary.scans_total.toLocaleString(),
			sub: latest ? SCAN_STATUS_LABEL[latest.status] : null,
			tone: 'muted',
			bars: [],
			href: ROUTES.scansForTarget(targetId),
			hint: latest ? `${latest.engine_name} · ${SCAN_STATUS_LABEL[latest.status]}` : 'No runs',
			dot: latest ? SCAN_STATUS_DOT[latest.status] : undefined,
			meta: latest
				? live
					? (run?.stage?.title ?? latest.engine_name)
					: `${when} · ${latest.engine_name}`
				: undefined
		});
		for (const spec of SURFACE_ORDER) {
			const m = summary.surface.find((x) => x.key === spec.key);
			if (!m) continue;
			const note = noteFor(m);
			out.push({
				key: spec.key,
				label: spec.label,
				value: m.value == null ? '—' : m.value.toLocaleString(),
				sub: note.text,
				tone: note.tone,
				bars: trendFor(spec.key),
				href: m.covered && m.scan_id ? ROUTES.scanTab(m.scan_id, spec.tab) : null,
				hint: m.covered
					? `Open ${spec.label} in the run that observed them${m.observed_at ? ` · ${formatShortDate(m.observed_at)}` : ''}`
					: `${spec.label} not scanned`
			});
		}
		return out;
	});

	function bars(values: number[]): { x: number; y: number; w: number; h: number }[] {
		const max = Math.max(1, ...values);
		const slot = W / Math.max(1, values.length);
		return values.map((v, i) => {
			const h = v ? Math.max(2, (v / max) * (H - 2)) : 0;
			return { x: i * slot + 0.5, y: H - h, w: Math.max(1, slot - 1.5), h };
		});
	}
	const TONE: Record<Tile['tone'], string> = {
		muted: 'text-muted-foreground',
		up: 'font-medium text-foreground',
		down: 'text-muted-foreground',
		warn: 'font-medium text-warning',
		bad: 'font-medium text-destructive'
	};
</script>

{#if loading && !summary}
	<div
		class="grid grid-cols-2 overflow-hidden rounded-xl border bg-card md:grid-cols-4 xl:grid-cols-7"
	>
		{#each Array(7) as _, i (i)}
			<div class="-mr-px -mb-px flex flex-col gap-2 border-r border-b px-4 py-3">
				<Skeleton class="h-3 w-16" />
				<Skeleton class="h-6 w-12" />
				<Skeleton class="h-3 w-20" />
			</div>
		{/each}
	</div>
{:else if scanned}
	<div
		class="grid grid-cols-2 overflow-hidden rounded-xl border bg-card md:grid-cols-4 xl:grid-cols-7"
	>
		{#each tiles as t, i (t.key)}
			<Hint text={t.hint}>
				{#snippet child(props)}
					<svelte:element
						this={t.href ? 'a' : 'div'}
						{...props}
						href={t.href ?? undefined}
						class="group -mr-px -mb-px flex min-w-0 flex-col gap-1 border-r border-b px-4 py-3 text-left transition-colors {t.href
							? 'hover:bg-muted/40 focus-visible:bg-muted/40 focus-visible:outline-none'
							: ''} {i === tiles.length - 1 ? 'col-span-2 xl:col-span-1' : ''}"
					>
						<span class="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
							{t.label}
						</span>
						<span
							class="text-2xl leading-none font-semibold tracking-tight tabular-nums {t.value ===
							'—'
								? 'text-muted-foreground'
								: ''}"
						>
							{t.value}
						</span>
						<span class="flex h-4 min-w-0 items-center gap-1.5 text-xs tabular-nums {TONE[t.tone]}">
							{#if t.dot}
								<span class="size-2 shrink-0 rounded-full border-2 {t.dot}" aria-hidden="true"
								></span>
							{/if}
							<span class="truncate">{t.sub ?? ''}</span>
						</span>
						{#if t.bars.length}
							<svg
								viewBox="0 0 {W} {H}"
								class="mt-1 h-5 w-full"
								preserveAspectRatio="none"
								aria-hidden="true"
							>
								<line x1="0" x2={W} y1={H - 0.5} y2={H - 0.5} class="stroke-border" />
								{#each bars(t.bars) as b, j (j)}
									{#if b.h}
										<rect x={b.x} y={b.y} width={b.w} height={b.h} class="fill-series" />
									{/if}
								{/each}
							</svg>
						{:else if t.meta}
							<span class="mt-1 flex h-5 min-w-0 items-center text-2xs text-muted-foreground">
								<span class="truncate">{t.meta}</span>
							</span>
						{:else}
							<span class="mt-1 h-5"></span>
						{/if}
					</svelte:element>
				{/snippet}
			</Hint>
		{/each}
	</div>
{:else}
	<div
		class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-dashed px-4 py-3"
	>
		<p class="text-sm text-muted-foreground">Not scanned</p>
		<Button size="sm" class="gap-1.5" onclick={onScan}>
			<Play class="size-3.5" /> Start scan
		</Button>
	</div>
{/if}
