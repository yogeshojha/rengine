<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import SignalSheet, { type SheetRow } from './signal-sheet.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE_ORDER, type SurfaceSpec } from '$lib/config/surface';
	import { relativeTime } from '$lib/utilities/dates';
	import { windowDays, type DashboardOverview, type DashboardWindow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		onScan: (ids: string[]) => void;
	}

	let { overview, window, onScan }: Props = $props();

	let days = $derived(windowDays(window));
	let recent = $derived(overview.daily.slice(-days));

	interface Tile {
		key: string;
		label: string;
		value: number;
		added: number;
		retired: number;
		bars: number[];
		note: string | null;
		spec: SurfaceSpec | null;
	}

	let tiles = $derived.by<Tile[]>(() => {
		const out: Tile[] = [
			{
				key: 'targets',
				label: 'Targets',
				value: overview.targets_total,
				added: 0,
				retired: 0,
				bars: [],
				note: `${overview.targets_scanned} of ${overview.targets_total} scanned`,
				spec: null
			}
		];
		for (const spec of SURFACE_ORDER) {
			const key = spec.key;
			const metric = overview.surface.find((m) => m.key === key);
			if (!metric) continue;
			out.push({
				key,
				label: spec.label,
				value: metric.value,
				added: recent.reduce((n, d) => n + (d.new[key] ?? 0), 0),
				retired: recent.reduce((n, d) => n + (d.retired[key] ?? 0), 0),
				bars: recent.map((d) => d.new[key] ?? 0),
				note:
					metric.targets_covered < overview.targets_total
						? `${metric.targets_covered} of ${overview.targets_total} targets`
						: null,
				spec
			});
		}
		return out;
	});

	const W = 120;
	const H = 22;
	function bars(values: number[]): { x: number; y: number; w: number; h: number }[] {
		const max = Math.max(1, ...values);
		const slot = W / Math.max(1, values.length);
		return values.map((v, i) => {
			const h = v ? Math.max(2, (v / max) * (H - 2)) : 0;
			return { x: i * slot + 0.5, y: H - h, w: Math.max(1, slot - 1.5), h };
		});
	}
	const hint = (t: Tile) =>
		t.spec
			? `${t.added.toLocaleString()} added${t.retired ? `, ${t.retired.toLocaleString()} retired` : ''} in ${days} days`
			: `${overview.targets_never_scanned} never scanned`;

	let sheetOpen = $state(false);
	let sheetTile = $state<Tile | null>(null);
	let sheetRows = $derived.by<SheetRow[]>(() => {
		const t = sheetTile;
		if (!t) return [];
		if (!t.spec) {
			return overview.targets.map((row) => ({
				key: row.id,
				primary: row.value,
				secondary: row.last_scan_at ? `Last run ${relativeTime(row.last_scan_at)}` : 'Not scanned',
				meta: row.monitored ? 'scheduled' : undefined,
				href: ROUTES.target(row.id),
				group: row.last_scan_at ? 'Scanned' : 'Not scanned'
			}));
		}
		const spec = t.spec;
		return overview.targets
			.map((row) => ({ row, s: row.surface.find((x) => x.key === spec.key) }))
			.sort((a, b) => (b.s?.value ?? -1) - (a.s?.value ?? -1))
			.map(({ row, s }) => {
				const covered = !!s?.covered && s.value !== null;
				const delta = s?.delta ?? null;
				const value = s?.value ?? 0;
				return {
					key: row.id,
					primary: row.value,
					secondary: covered
						? `${value.toLocaleString()} ${spec.label.toLowerCase()}${s?.observed_at ? ` · ${relativeTime(s.observed_at)}` : ''}`
						: 'Not scanned',
					meta:
						delta === null
							? undefined
							: `${delta > 0 ? '▲' : delta < 0 ? '▼' : ''} ${Math.abs(delta).toLocaleString()}`,
					tone: delta !== null && delta > 0 ? ('warn' as const) : undefined,
					href: covered && s?.scan_id ? ROUTES.scanTab(s.scan_id, spec.tab) : ROUTES.target(row.id),
					group: covered ? 'Scanned' : 'Not scanned'
				};
			});
	});
	let unscanned = $derived.by(() => {
		const t = sheetTile;
		if (!t) return [] as string[];
		if (!t.spec) return overview.targets.filter((r) => !r.last_scan_at).map((r) => r.id);
		const spec = t.spec;
		return overview.targets
			.filter((r) => !r.surface.find((x) => x.key === spec.key)?.covered)
			.map((r) => r.id);
	});
	function open(t: Tile) {
		sheetTile = t;
		sheetOpen = true;
	}
</script>

<div
	class="grid grid-cols-2 overflow-hidden rounded-xl border bg-card md:grid-cols-4 xl:grid-cols-7"
>
	{#each tiles as t (t.key)}
		<Hint text={hint(t)}>
			{#snippet child(props)}
				<button
					{...props}
					type="button"
					class="group -mr-px -mb-px flex min-w-0 flex-col gap-1 border-r border-b px-4 py-3 text-left transition-colors hover:bg-muted/40 focus-visible:bg-muted/40 focus-visible:outline-none"
					onclick={() => open(t)}
				>
					<span class="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
						{t.label}
					</span>
					<span class="text-2xl leading-none font-semibold tracking-tight tabular-nums">
						{t.value.toLocaleString()}
					</span>
					<span class="flex h-4 items-center gap-2 text-xs tabular-nums">
						{#if t.bars.length}
							<span class="font-medium {t.added ? '' : 'text-muted-foreground'}">
								▲ {t.added.toLocaleString()}
							</span>
							{#if t.retired}
								<span class="text-muted-foreground">▼ {t.retired.toLocaleString()}</span>
							{/if}
						{:else if t.note}
							<span class="text-muted-foreground">{t.note}</span>
						{/if}
					</span>
					{#if t.bars.length}
						<svg
							viewBox="0 0 {W} {H}"
							class="mt-1 h-5 w-full"
							preserveAspectRatio="none"
							aria-hidden="true"
						>
							<line x1="0" x2={W} y1={H - 0.5} y2={H - 0.5} class="stroke-border" />
							{#each bars(t.bars) as b, i (i)}
								{#if b.h}
									<rect x={b.x} y={b.y} width={b.w} height={b.h} class="fill-series" />
								{/if}
							{/each}
						</svg>
					{:else}
						<span class="mt-1 h-5"></span>
					{/if}
				</button>
			{/snippet}
		</Hint>
	{/each}
</div>

<SignalSheet
	open={sheetOpen}
	onOpenChange={(o) => (sheetOpen = o)}
	title={sheetTile?.label ?? ''}
	description={sheetTile
		? sheetTile.spec
			? `${sheetTile.value.toLocaleString()} across ${overview.targets_total} targets`
			: `${overview.targets_scanned} of ${overview.targets_total} scanned`
		: undefined}
	rows={sheetRows}
	noun="Targets"
	action={unscanned.length
		? {
				label: `Scan ${unscanned.length} ${unscanned.length === 1 ? 'target' : 'targets'}`,
				onClick: () => onScan(unscanned)
			}
		: null}
/>
