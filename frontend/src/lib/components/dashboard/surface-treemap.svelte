<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import Widget from './widget.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { SEVERITY_FILL, SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import type { DashboardOverview, DashboardTargetRow } from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		class?: string;
	}

	let { overview, class: className = '' }: Props = $props();

	const HEIGHT = 236;
	const GAP = 3;
	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	interface Leaf {
		id: string;
		label: string;
		value: number;
		findings: number;
		kev: number;
		severity: string | null;
	}
	interface Rect {
		leaf: Leaf;
		x: number;
		y: number;
		w: number;
		h: number;
	}

	let width = $state(0);
	let leaves = $derived<Leaf[]>(
		overview.targets
			.map((t: DashboardTargetRow) => ({
				id: t.id,
				label: t.value,
				value: t.surface.find((s) => s.key === WEB.key)?.value ?? 0,
				findings: t.findings,
				kev: t.kev,
				severity: t.worst_severity
			}))
			.filter((l) => l.value > 0)
			.sort((a, b) => b.value - a.value)
	);
	let total = $derived(leaves.reduce((n, l) => n + l.value, 0));

	// squarified layout
	function squarify(items: Leaf[], w: number, h: number): Rect[] {
		const out: Rect[] = [];
		if (!items.length || w <= 0 || h <= 0) return out;
		const scale = (w * h) / items.reduce((n, l) => n + l.value, 0);
		let x = 0;
		let y = 0;
		let rw = w;
		let rh = h;
		let row: Leaf[] = [];
		const worst = (r: Leaf[], side: number) => {
			const sum = r.reduce((n, l) => n + l.value * scale, 0);
			let max = 0;
			for (const l of r) {
				const a = l.value * scale;
				const ratio = Math.max((side * side * a) / (sum * sum), (sum * sum) / (side * side * a));
				max = Math.max(max, ratio);
			}
			return max;
		};
		const flush = () => {
			const sum = row.reduce((n, l) => n + l.value * scale, 0);
			const horizontal = rw >= rh;
			const side = horizontal ? rh : rw;
			const thick = sum / side;
			let offset = 0;
			for (const l of row) {
				const len = (l.value * scale) / thick;
				out.push(
					horizontal
						? { leaf: l, x, y: y + offset, w: thick, h: len }
						: { leaf: l, x: x + offset, y, w: len, h: thick }
				);
				offset += len;
			}
			if (horizontal) {
				x += thick;
				rw -= thick;
			} else {
				y += thick;
				rh -= thick;
			}
			row = [];
		};
		for (const item of items) {
			const side = Math.min(rw, rh);
			if (row.length && worst([...row, item], side) > worst(row, side)) flush();
			row.push(item);
		}
		if (row.length) flush();
		return out;
	}

	let rects = $derived(squarify(leaves, Math.max(0, width), HEIGHT));

	function fill(l: Leaf): string {
		const base = l.severity ? (SEVERITY_FILL[l.severity] ?? 'var(--series)') : 'var(--series)';
		const wash = l.severity ? 34 : 18;
		return `color-mix(in oklch, ${base} ${wash}%, transparent)`;
	}
	function edge(l: Leaf): string {
		return l.severity ? (SEVERITY_FILL[l.severity] ?? 'var(--series)') : 'var(--series)';
	}
	function hint(l: Leaf): string {
		const parts = [
			`${plural(l.value, WEB.noun, WEB.nounPlural)} · ${total ? Math.round((l.value / total) * 100) : 0}% of the estate`
		];
		if (l.findings)
			parts.push(
				`${plural(l.findings, 'finding', 'findings')}${l.severity ? `, worst ${SEVERITY_LABELS[l.severity] ?? l.severity}` : ''}${l.kev ? `, ${l.kev} known exploited` : ''}`
			);
		return parts.join(' · ');
	}
</script>

<Widget
	title="Web assets by target"
	description="Targets sized by {WEB.nounPlural} and tinted by worst severity"
	class={className}
>
	<div class="px-5 py-4">
		<div class="relative w-full" style="height:{HEIGHT}px" bind:clientWidth={width}>
			{#each rects as r (r.leaf.id)}
				{@const inner = { w: Math.max(0, r.w - GAP), h: Math.max(0, r.h - GAP) }}
				<Hint text={hint(r.leaf)}>
					{#snippet child(props)}
						<a
							{...props}
							href={ROUTES.target(r.leaf.id)}
							class="absolute flex flex-col overflow-hidden rounded-md border p-1.5 text-left transition-[filter] hover:brightness-95 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none dark:hover:brightness-125"
							style="left:{r.x}px;top:{r.y}px;width:{inner.w}px;height:{inner.h}px;background:{fill(
								r.leaf
							)};border-color:color-mix(in oklch, {edge(r.leaf)} 45%, transparent)"
							aria-label="{r.leaf.label}: {r.leaf.value} {WEB.nounPlural}"
						>
							{#if inner.w > 72 && inner.h > 30}
								<span class="truncate font-mono text-[11px] leading-4 font-medium">
									{r.leaf.label}
								</span>
								<span class="text-[11px] leading-4 text-muted-foreground tabular-nums">
									{r.leaf.value.toLocaleString()}
									{#if r.leaf.findings && inner.h > 46}
										<span class="block" style="color:{edge(r.leaf)}">
											{plural(r.leaf.findings, 'finding', 'findings')}
										</span>
									{/if}
								</span>
							{/if}
						</a>
					{/snippet}
				</Hint>
			{/each}
		</div>
	</div>
	{#snippet footer()}
		{plural(leaves.length, 'target', 'targets')} · {plural(total, WEB.noun, WEB.nounPlural)} in total
	{/snippet}
</Widget>
