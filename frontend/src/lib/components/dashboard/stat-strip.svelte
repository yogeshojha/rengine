<script lang="ts">
	import Target from '@lucide/svelte/icons/target';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ScanTrendSparkline from '$lib/components/scans/scan-trend-sparkline.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE_ORDER, type SurfaceSpec } from '$lib/config/surface';
	import type { IconComponent } from '$lib/config/icons';
	import {
		DASHBOARD_WINDOWS,
		type DashboardOverview,
		type DashboardWindow
	} from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview | null;
		window: DashboardWindow;
	}

	let { overview, window }: Props = $props();

	interface Tile {
		key: string;
		label: string;
		icon: IconComponent;
		value: number;
		href: string;
		fresh: number;
		freshHref?: string;
		freshNoun: string;
		note: string;
		spark: number[];
		sparkLabel: string;
	}

	let days = $derived(window === '30d' ? 30 : 7);
	let recent = $derived((overview?.daily ?? []).slice(-days));
	let windowLabel = $derived(DASHBOARD_WINDOWS.find((w) => w.key === window)?.label ?? window);
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let tiles = $derived.by<Tile[]>(() => {
		if (!overview) return [];
		const targets: Tile = {
			key: 'targets',
			label: 'Targets',
			icon: Target,
			value: overview.targets_total,
			href: ROUTES.targets,
			fresh: overview.runs_in_window,
			freshNoun: overview.runs_in_window === 1 ? 'run' : 'runs',
			note:
				overview.targets_never_scanned > 0
					? `${overview.targets_never_scanned} not scanned`
					: `${plural(overview.targets_scanned, 'target', 'targets')} scanned`,
			spark: recent.map((d) => d.runs),
			sparkLabel: 'Runs'
		};
		const dims = SURFACE_ORDER.map((spec: SurfaceSpec): Tile => {
			const m = overview.surface.find((s) => s.key === spec.key);
			return {
				key: spec.key,
				label: spec.label,
				icon: spec.icon,
				value: m?.value ?? 0,
				href: ROUTES.surface(spec.tab),
				fresh: m?.new_in_window ?? 0,
				freshHref: ROUTES.surface(spec.tab, { [spec.queryParam]: 'is:new' }),
				freshNoun: 'new',
				note: `${m?.targets_covered ?? 0} of ${plural(overview.targets_total, 'target', 'targets')}`,
				spark: recent.map((d) => d.new[spec.key] ?? 0),
				sparkLabel: `New ${spec.nounPlural}`
			};
		});
		return [targets, ...dims];
	});
</script>

<div
	class="grid grid-cols-2 gap-px overflow-hidden rounded-xl border bg-border md:grid-cols-4 xl:grid-cols-7"
>
	{#if !overview}
		{#each Array(6) as _, i (i)}
			<div class="flex flex-col gap-3 bg-card p-4">
				<Skeleton class="h-4 w-20" />
				<Skeleton class="h-8 w-24" />
				<Skeleton class="h-4 w-28" />
			</div>
		{/each}
	{:else}
		{#each tiles as t (t.key)}
			<div
				class="group relative flex flex-col gap-2 bg-card p-4 transition-colors hover:bg-muted/30"
			>
				<a
					href={t.href}
					class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground group-hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					<t.icon class="size-3.5" />
					{t.label}
				</a>
				<div class="flex items-end justify-between gap-2">
					<a
						href={t.href}
						class="text-2xl leading-none font-semibold tracking-tight tabular-nums focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					>
						{t.value.toLocaleString()}
					</a>
					{#if t.spark.some((v) => v > 0)}
						<ScanTrendSparkline values={t.spark} label={t.sparkLabel} class="h-7 w-20" />
					{/if}
				</div>
				<div class="flex flex-col gap-0.5 text-xs">
					{#if t.fresh > 0}
						<svelte:element
							this={t.freshHref ? 'a' : 'span'}
							href={t.freshHref}
							class="truncate font-medium text-success tabular-nums {t.freshHref
								? 'hover:underline'
								: ''}"
						>
							{t.freshHref ? '▲ ' : ''}{t.fresh.toLocaleString()}
							{t.freshNoun} in {windowLabel}
						</svelte:element>
					{:else}
						<span class="truncate text-muted-foreground">
							{t.key === 'targets' ? 'No runs' : 'No change'} in {windowLabel}
						</span>
					{/if}
					<span class="truncate text-muted-foreground">{t.note}</span>
				</div>
			</div>
		{/each}
	{/if}
</div>
