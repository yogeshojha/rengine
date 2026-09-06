<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import Crosshair from '@lucide/svelte/icons/crosshair';
	import Plus from '@lucide/svelte/icons/plus';
	import Play from '@lucide/svelte/icons/play';
	import * as Card from '$lib/components/ui/card';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import Hint from '$lib/components/hint.svelte';
	import GeoPanel from './geo-panel.svelte';
	import SignalSheet, { type SheetAction, type SheetRow } from './signal-sheet.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { ROUTES } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';
	import { SURFACE, SurfaceDimension, surfaceSpec } from '$lib/config/surface';
	import { formatTargetType, type TargetType } from '$lib/types/target';
	import { relativeTime } from '$lib/utilities/dates';
	import { formatSeconds, isLiveStatus, SCAN_STATUS_LABEL } from '$lib/utilities/scan-status';
	import {
		DASHBOARD_WINDOWS,
		windowText,
		type DashboardOverview,
		type DashboardTargetRow,
		type DashboardWindow
	} from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview | null;
		loading: boolean;
		window: DashboardWindow;
		now: number;
		onWindow: (w: DashboardWindow) => void;
		onChanges: (key: SurfaceDimension) => void;
		onScan: () => void;
		onScanTargets: (ids: string[]) => void;
		onAddTarget: () => void;
	}

	let {
		overview,
		loading,
		window,
		now,
		onWindow,
		onChanges,
		onScan,
		onScanTargets,
		onAddTarget
	}: Props = $props();

	const MAX_LIVE = 3;
	const TARGETS_CELL = 'targets';
	type CellKey = typeof TARGETS_CELL | SurfaceDimension;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;
	const typeLabel = (t: string) => formatTargetType(t as TargetType);

	let risk = $derived(overview?.risk ?? null);
	let sev = (key: string) => risk?.by_severity.find((s) => s.severity === key)?.count ?? 0;
	let kevTargets = $derived(overview?.targets.filter((t) => t.kev > 0).length ?? 0);
	let criticalTargets = $derived(
		overview?.targets.filter((t) => t.worst_severity === 'critical').length ?? 0
	);
	let sensitiveTotal = $derived(overview?.sensitive.reduce((n, s) => n + s.count, 0) ?? 0);
	let newest = $derived(
		[...(overview?.surface ?? [])].sort((a, b) => b.new_in_window - a.new_in_window)[0] ?? null
	);
	let windowLabel = $derived(windowText(window));
	let noTargets = $derived(!!overview && overview.targets_total === 0);
	let unscanned = $derived(
		!!overview && overview.targets_total > 0 && overview.targets_scanned === 0
	);

	let headline = $derived.by(() => {
		if (!overview || !risk) return '';
		if (noTargets) return 'No targets yet';
		if (unscanned)
			return `${plural(overview.targets_total, 'target', 'targets')}, none scanned yet`;
		if (risk.kev > 0)
			return `${plural(risk.kev, 'known-exploited vulnerability', 'known-exploited vulnerabilities')} across ${plural(kevTargets, 'target', 'targets')}`;
		const critical = sev('critical');
		if (critical > 0)
			return `${plural(critical, 'critical finding', 'critical findings')} across ${plural(criticalTargets, 'target', 'targets')}`;
		const high = sev('high');
		if (high > 0) return `${plural(high, 'high finding', 'high findings')} to review`;
		if (sensitiveTotal > 0)
			return `${plural(sensitiveTotal, 'sensitive service', 'sensitive services')} exposed across ${plural(overview.sensitive.length, 'target', 'targets')}`;
		if (overview.signals.takeover.count > 0)
			return plural(overview.signals.takeover.count, 'takeover candidate', 'takeover candidates');
		if (newest && newest.new_in_window > 0) {
			const spec = surfaceSpec(newest.key);
			return `${plural(newest.new_in_window, spec?.noun ?? newest.key, spec?.nounPlural ?? newest.key)} discovered in the ${windowLabel}`;
		}
		return overview.runs_in_window > 0
			? `No change in the ${windowLabel}`
			: 'Nothing needs attention';
	});

	let subline = $derived.by(() => {
		if (!overview) return '';
		if (noTargets) return 'Add a target to start mapping the attack surface.';
		if (unscanned)
			return 'Start a scan to establish the baseline every later run is compared against.';
		const parts = [
			plural(overview.targets_total, 'target', 'targets'),
			plural(overview.runs_total, 'run', 'runs')
		];
		if (overview.last_completed_at)
			parts.push(`last completed ${relativeTime(overview.last_completed_at)}`);
		if (overview.targets_never_scanned > 0)
			parts.push(`${overview.targets_never_scanned} never scanned`);
		if (overview.targets_monitored > 0) parts.push(`${overview.targets_monitored} monitored`);
		return parts.join(' · ');
	});

	let changes = $derived(
		(overview?.surface ?? [])
			.filter((m) => m.new_in_window > 0)
			.map((m) => ({ ...m, spec: surfaceSpec(m.key) }))
	);
	let live = $derived(liveScans.scans.slice(0, MAX_LIVE));
	let liveMore = $derived(liveScans.scans.length - live.length);
	let showGeo = $derived(
		!!overview && (overview.geography.length > 0 || (loading && overview.geo_total > 0))
	);
	interface Cell {
		key: CellKey;
		label: string;
		noun: string;
		icon: IconComponent | undefined;
		value: number;
		covered: boolean;
		note: string;
		fresh: number;
	}
	let cells = $derived.by<Cell[]>(() => {
		if (!overview) return [];
		const total = overview.targets_total;
		const coverage: string[] = [];
		if (overview.targets_scanned === total) coverage.push('all scanned');
		else coverage.push(`${overview.targets_scanned} scanned`);
		if (overview.targets_never_scanned > 0)
			coverage.push(`${overview.targets_never_scanned} never`);
		else if (overview.targets_stale > 0) coverage.push(`${overview.targets_stale} stale`);
		const out: Cell[] = [
			{
				key: TARGETS_CELL,
				label: 'Targets',
				noun: 'targets',
				icon: Crosshair,
				value: total,
				covered: total > 0,
				note: coverage.join(' · '),
				fresh: 0
			}
		];
		for (const m of overview.surface) {
			const spec = surfaceSpec(m.key);
			out.push({
				key: m.key as SurfaceDimension,
				label: spec?.label ?? m.label,
				noun: spec?.nounPlural ?? m.label,
				icon: spec?.icon,
				value: m.value,
				covered: m.targets_covered > 0,
				note: `${m.targets_covered} of ${total} targets`,
				fresh: m.new_in_window
			});
		}
		return out;
	});

	function liveDetail(scanId: string, startedAt: string | null, createdAt: string): string {
		const run = liveScans.runFor(scanId);
		const parts: string[] = [];
		if (run?.stage?.title) parts.push(run.stage.title);
		const started = startedAt ?? createdAt;
		const elapsed = Math.max(0, Math.floor((now - new Date(started).getTime()) / 1000));
		if (startedAt) parts.push(formatSeconds(elapsed));
		return parts.join(' · ');
	}

	interface SheetState {
		title: string;
		description?: string;
		rows: SheetRow[];
		action?: SheetAction | null;
	}
	let sheet = $state<SheetState | null>(null);
	let sheetOpen = $state(false);
	const at = (iso: string | null) => (iso ? new Date(iso).getTime() : 0);

	function runText(t: DashboardTargetRow): string {
		if (!t.last_scan_status) return '';
		if (isLiveStatus(t.last_scan_status))
			return liveScans.runFor(t.last_scan_id ?? '')?.stage?.title ?? 'Running';
		const status = t.last_scan_status === 'completed' ? '' : SCAN_STATUS_LABEL[t.last_scan_status];
		return [status, `last run ${relativeTime(t.last_scan_at)}`].filter(Boolean).join(' · ');
	}
	function scanAction(ids: string[]): SheetAction | null {
		if (!ids.length) return null;
		return {
			label: ids.length === 1 ? 'Scan this target' : `Scan these ${ids.length} targets`,
			onClick: () => {
				sheetOpen = false;
				onScanTargets(ids);
			}
		};
	}
	function openTargets() {
		if (!overview) return;
		const scanned = overview.targets
			.filter((t) => t.last_scan_status)
			.sort((a, b) => at(b.last_scan_at) - at(a.last_scan_at));
		const rows: SheetRow[] = scanned.map((t) => ({
			key: t.id,
			group: 'Scanned',
			primary: t.value,
			secondary: runText(t),
			meta: plural(t.scans_total, 'run', 'runs'),
			href: ROUTES.target(t.id)
		}));
		for (const t of overview.stale)
			rows.push({
				key: t.target_id,
				group: 'Not scanned in 30 days',
				primary: t.target_value,
				secondary: t.last_scanned_at ? `last run ${relativeTime(t.last_scanned_at)}` : undefined,
				href: ROUTES.target(t.target_id)
			});
		for (const t of overview.never_scanned)
			rows.push({
				key: t.target_id,
				group: 'Never scanned',
				primary: t.target_value,
				secondary: typeLabel(t.target_type),
				href: ROUTES.target(t.target_id)
			});
		sheet = {
			title: 'Targets',
			description: 'Every target in the project and how current its surface is',
			rows,
			action: scanAction([
				...overview.stale.map((t) => t.target_id),
				...overview.never_scanned.map((t) => t.target_id)
			])
		};
		sheetOpen = true;
	}
	function deltaText(delta: number | null, observedAt: string | null): string {
		if (delta == null) return observedAt ? `observed ${relativeTime(observedAt)}` : '';
		if (delta > 0) return `+${delta.toLocaleString()} since the previous run`;
		if (delta < 0) return `−${Math.abs(delta).toLocaleString()} since the previous run`;
		return 'No change since the previous run';
	}
	function openDimension(key: SurfaceDimension) {
		if (!overview) return;
		const spec = SURFACE[key];
		const covered: {
			t: DashboardTargetRow;
			value: number;
			delta: number | null;
			scanId: string;
			observed: string | null;
		}[] = [];
		const missing: DashboardTargetRow[] = [];
		for (const t of overview.targets) {
			const m = t.surface.find((s) => s.key === key);
			if (m?.covered && m.scan_id)
				covered.push({
					t,
					value: m.value ?? 0,
					delta: m.delta,
					scanId: m.scan_id,
					observed: m.observed_at
				});
			else missing.push(t);
		}
		covered.sort((a, b) => b.value - a.value || a.t.value.localeCompare(b.t.value));
		const rows: SheetRow[] = covered.map((c) => ({
			key: c.t.id,
			group: 'Scanned',
			primary: c.t.value,
			secondary: deltaText(c.delta, c.observed),
			meta: c.value.toLocaleString(),
			href: ROUTES.scanTab(c.scanId, spec.tab)
		}));
		for (const t of missing)
			rows.push({
				key: t.id,
				group: 'Not scanned',
				primary: t.value,
				secondary: typeLabel(t.type),
				href: ROUTES.target(t.id)
			});
		sheet = {
			title: `${spec.label} by target`,
			description: `What the latest run covering ${spec.nounPlural} found on each target`,
			rows,
			action: scanAction(missing.map((t) => t.id))
		};
		sheetOpen = true;
	}
	function openCell(c: Cell) {
		if (c.key === TARGETS_CELL) openTargets();
		else openDimension(c.key);
	}
</script>

{#snippet cellBody(c: Cell)}
	{@const Icon = c.icon}
	<span class="flex items-center gap-1.5 text-xs text-muted-foreground group-hover:text-foreground">
		{#if Icon}<Icon class="size-3.5" />{/if}
		{c.label}
	</span>
	<span
		class="text-2xl leading-none font-semibold tracking-tight tabular-nums {c.covered
			? ''
			: 'font-medium text-muted-foreground'}"
	>
		{c.covered ? c.value.toLocaleString() : '—'}
	</span>
	<span class="flex h-4 items-center gap-2 text-xs tabular-nums">
		{#if !c.covered}
			<span class="text-muted-foreground">Not scanned</span>
		{:else}
			<span class="truncate text-muted-foreground">{c.note}</span>
			{#if c.fresh > 0}
				<span class="inline-flex shrink-0 items-center text-success">
					<ArrowUpRight class="size-3" />{c.fresh.toLocaleString()}
				</span>
			{/if}
		{/if}
	</span>
{/snippet}

<Card.Root class="gap-0 overflow-hidden py-0">
	<div
		class="grid {showGeo
			? 'lg:grid-cols-[minmax(0,1fr)_19rem] xl:grid-cols-[minmax(0,1fr)_22rem]'
			: ''}"
	>
		<div class="flex min-w-0 flex-col">
			<div class="flex flex-col gap-2 px-5 pt-5 pb-5">
				<div class="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
					<div class="flex min-w-0 flex-col gap-2">
						{#if !overview}
							<Skeleton class="h-7 w-80" />
							<Skeleton class="h-4 w-64" />
						{:else}
							<h2 class="text-xl font-semibold tracking-tight sm:text-2xl">{headline}</h2>
							<p class="text-sm text-muted-foreground">{subline}</p>
						{/if}
					</div>
					{#if overview && !noTargets}
						<ToggleGroup.Root
							type="single"
							variant="outline"
							size="sm"
							value={window}
							onValueChange={(v) => v && onWindow(v as DashboardWindow)}
							aria-label="Change window"
						>
							{#each DASHBOARD_WINDOWS as w (w.key)}
								<ToggleGroup.Item value={w.key} class="px-2.5" aria-label={w.text}>
									{w.label}
								</ToggleGroup.Item>
							{/each}
						</ToggleGroup.Root>
					{/if}
				</div>

				{#if noTargets}
					<div class="mt-1">
						<Button size="sm" class="gap-1.5" onclick={onAddTarget}>
							<Plus class="size-3.5" /> Add target
						</Button>
					</div>
				{:else if unscanned}
					<div class="mt-1">
						<Button size="sm" class="gap-1.5" onclick={onScan}>
							<Play class="size-3.5" /> Start scan
						</Button>
					</div>
				{:else if overview && (changes.length || live.length)}
					<div class="mt-1 flex flex-wrap items-center gap-2">
						{#each live as s (s.id)}
							<a
								href={ROUTES.scan(s.id)}
								class="inline-flex h-6 items-center gap-1.5 rounded-md border border-info/40 bg-info/5 px-2 text-xs transition-colors hover:bg-info/10"
							>
								<Spinner class="size-3 text-info" />
								<span class="font-mono">{s.execution_config.target_value}</span>
								<span class="text-muted-foreground">
									{liveDetail(s.id, s.started_at, s.created_at) || SCAN_STATUS_LABEL[s.status]}
								</span>
							</a>
						{/each}
						{#if liveMore > 0}
							<a
								href={ROUTES.scans}
								class="inline-flex h-6 items-center rounded-md border border-dashed px-2 text-xs text-muted-foreground hover:text-foreground"
							>
								+{liveMore} more running
							</a>
						{/if}
						{#each changes as c (c.key)}
							<button
								type="button"
								class="inline-flex h-6 items-center gap-1 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60"
								onclick={() => onChanges(c.key as SurfaceDimension)}
								aria-label="Show new {c.spec?.nounPlural ?? c.key} in the {windowLabel}"
							>
								<ArrowUpRight class="size-3.5 text-success" />
								<span class="font-medium tabular-nums">{c.new_in_window.toLocaleString()}</span>
								new {c.spec?.nounPlural ?? c.key}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			{#if overview && !noTargets}
				<div class="mt-auto -ml-px grid grid-cols-2 sm:grid-cols-3">
					{#each cells as c (c.key)}
						{#if c.covered}
							<Hint text="Show {c.noun} by target">
								{#snippet child(props)}
									<button
										{...props}
										type="button"
										class="group flex min-w-0 cursor-pointer flex-col gap-1.5 border-t border-l px-5 py-4 text-left transition-colors hover:bg-muted/40"
										onclick={() => openCell(c)}
									>
										{@render cellBody(c)}
									</button>
								{/snippet}
							</Hint>
						{:else}
							<Hint text="No scan has covered {c.noun} yet">
								{#snippet child(props)}
									<div
										{...props}
										class="group flex min-w-0 flex-col gap-1.5 border-t border-l border-dashed px-5 py-4 text-left"
									>
										{@render cellBody(c)}
									</div>
								{/snippet}
							</Hint>
						{/if}
					{/each}
				</div>
			{:else if !overview}
				<div class="mt-auto -ml-px grid grid-cols-2 sm:grid-cols-3">
					{#each Array(6) as _, i (i)}
						<div class="flex flex-col gap-2 border-t border-l px-5 py-4">
							<Skeleton class="h-3.5 w-20" />
							<Skeleton class="h-6 w-16" />
							<Skeleton class="h-3.5 w-24" />
						</div>
					{/each}
				</div>
			{/if}
		</div>

		{#if showGeo && overview}
			<GeoPanel
				geography={overview.geography}
				total={overview.geo_total}
				ready={!loading}
				class="border-t lg:border-t-0 lg:border-l"
			/>
		{/if}
	</div>
</Card.Root>

{#if sheet}
	<SignalSheet
		open={sheetOpen}
		onOpenChange={(v) => (sheetOpen = v)}
		title={sheet.title}
		description={sheet.description}
		rows={sheet.rows}
		action={sheet.action ?? null}
	/>
{/if}
