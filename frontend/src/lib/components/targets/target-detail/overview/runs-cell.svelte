<script lang="ts">
	import Cell from '$lib/components/cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SURFACE_ORDER, SurfaceDimension } from '$lib/config/surface';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		history: ScanRead[];
		class?: string;
	}

	let { history, class: className = '' }: Props = $props();

	const RUNS = 12;
	const W = 320;
	const H = 150;
	const PAD = { top: 6, left: 34, right: 8, bottom: 22 };

	let dimension = $state<SurfaceDimension>(SurfaceDimension.WEB_ASSETS);
	let spec = $derived(SURFACE[dimension]);
	let dimensions = $derived(SURFACE_ORDER.filter((s) => s.countColumns.length > 0));

	let runs = $derived(
		history
			.filter((s) => s.status === 'completed' && s.scope !== 'focused')
			.sort(
				(a, b) =>
					new Date(a.started_at ?? a.created_at).getTime() -
					new Date(b.started_at ?? b.created_at).getTime()
			)
			.slice(-RUNS)
	);
	let points = $derived(
		runs.map((s) => ({
			scan: s,
			value: Number(s[spec.countColumns[0]] ?? 0),
			at: s.started_at ?? s.created_at
		}))
	);
	let max = $derived(Math.max(1, ...points.map((p) => p.value)));
	let plotW = W - PAD.left - PAD.right;
	let plotH = H - PAD.top - PAD.bottom;
	let slot = $derived(plotW / Math.max(1, points.length));
	let barW = $derived(Math.max(4, Math.min(28, slot * 0.55)));
	const y = (v: number) => PAD.top + plotH - (v / max) * plotH;
	let ticks = $derived([0, max / 2, max].map((v) => ({ v, y: y(v) })));
	const fmt = (v: number) =>
		v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : Math.round(v).toString();
	let every = $derived(points.length <= 6 ? 1 : Math.ceil(points.length / 6));
	let first = $derived(points[0]?.value ?? 0);
	let last = $derived(points.at(-1)?.value ?? 0);
</script>

<Cell
	skeleton="bars"
	id="runs"
	title="Surface by run"
	description="{spec.label} each completed run"
	href={ROUTES.scansForTarget(runs[0]?.target_id ?? '')}
	hrefLabel="All runs"
	class={className}
>
	{#snippet tools()}
		<ToggleGroup.Root
			type="single"
			variant="outline"
			size="sm"
			value={dimension}
			onValueChange={(v) => v && (dimension = v as SurfaceDimension)}
			aria-label="Dimension"
		>
			{#each dimensions as d (d.key)}
				{@const Icon = d.icon}
				<Hint text={d.label}>
					{#snippet child(props)}
						<ToggleGroup.Item {...props} value={d.key} class="size-7 px-0" aria-label={d.label}>
							<Icon class="size-3.5" />
						</ToggleGroup.Item>
					{/snippet}
				</Hint>
			{/each}
		</ToggleGroup.Root>
	{/snippet}
	<svg viewBox="0 0 {W} {H}" class="h-[150px] w-full" preserveAspectRatio="none" aria-hidden="true">
		{#each ticks as t (t.v)}
			<line x1={PAD.left} x2={W - PAD.right} y1={t.y} y2={t.y} class="stroke-border/60" />
			<text x={PAD.left - 6} y={t.y + 3} text-anchor="end" class="fill-muted-foreground text-2xs"
				>{fmt(t.v)}</text
			>
		{/each}
		{#each points as p, i (p.scan.id)}
			{@const x = PAD.left + i * slot + slot / 2}
			<a href={ROUTES.scanTab(p.scan.id, spec.tab)}>
				<title
					>{p.value.toLocaleString()}
					{spec.nounPlural} · {p.scan.engine_name} · {formatShortDate(p.at)}</title
				>
				<rect
					x={x - barW / 2}
					y={y(p.value)}
					width={barW}
					height={Math.max(p.value ? 2 : 0, PAD.top + plotH - y(p.value))}
					rx="2"
					class="fill-series transition-opacity hover:opacity-80"
				/>
			</a>
			{#if i % every === 0 || i === points.length - 1}
				<text {x} y={H - 6} text-anchor="middle" class="fill-muted-foreground text-2xs">
					{formatShortDate(p.at)}
				</text>
			{/if}
		{/each}
	</svg>
	{#snippet footer()}
		<span class="tabular-nums">
			{first.toLocaleString()} → {last.toLocaleString()} over {points.length} runs
		</span>
	{/snippet}
</Cell>
