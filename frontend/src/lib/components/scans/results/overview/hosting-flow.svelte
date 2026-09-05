<script lang="ts">
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import type { FlowLink, FlowNode, HostingFlow } from '$lib/types/hosting-flow';

	interface Props {
		flow: HostingFlow;
		onPick: (query: string) => void;
	}

	let { flow, onPick }: Props = $props();

	const NODE_W = 10;
	const PAD = 8;
	const MIN_NODE = 12;
	const TOP = 24;
	const BOTTOM = 4;
	const LABEL_L = 110;
	const LABEL_R = 250;
	const MIN_H = 240;
	const MAX_H = 340;
	const LABEL_MAX = 30;
	const HIT_MIN = 12;
	const TIP_W = 288;
	const COLUMNS = ['Web assets', 'Fronting', 'Network'];
	const FILL: Record<string, string> = {
		edge: 'var(--chart-1)',
		cloud: 'var(--chart-3)',
		direct: 'var(--chart-2)',
		muted: 'color-mix(in oklch, var(--muted-foreground) 45%, transparent)'
	};

	interface Laid extends FlowNode {
		x0: number;
		x1: number;
		y0: number;
		y1: number;
		outY: number;
		inY: number;
	}
	interface LaidLink extends FlowLink {
		path: string;
		width: number;
		from: Laid;
		to: Laid;
		length: number;
	}
	interface Hover {
		nodes: Set<string>;
		links: Set<number>;
	}
	interface Tip {
		x: number;
		y: number;
		title: string;
		sub: string;
		query: string | null;
	}

	let width = $state(900);
	let hovered = $state<Hover | null>(null);
	let tip = $state<Tip | null>(null);
	let drawn = $state(false);
	let reduce = $state(false);
	let el = $state<HTMLDivElement | null>(null);

	let height = $derived(Math.max(MIN_H, Math.min(MAX_H, 40 + flow.nodes.length * 22)));

	const clip = (s: string) =>
		s.length > LABEL_MAX ? `${s.slice(0, LABEL_MAX - 1).trimEnd()}…` : s;
	const share = (n: number, of: number) => (of > 0 ? `${Math.round((n / of) * 100)}%` : '');

	let layout = $derived.by(() => {
		const inner = { x0: LABEL_L, x1: width - LABEL_R, y0: TOP, y1: height - BOTTOM };
		const span = inner.y1 - inner.y0;
		const cols: Laid[][] = [[], [], []];
		const nodes: Laid[] = flow.nodes.map((n) => ({
			...n,
			x0: 0,
			x1: 0,
			y0: 0,
			y1: 0,
			outY: 0,
			inY: 0
		}));
		for (const n of nodes) cols[n.column].push(n);
		const colX = (i: number) => inner.x0 + ((inner.x1 - inner.x0 - NODE_W) * i) / 2;
		let scale = Infinity;
		for (const col of cols) {
			if (!col.length) continue;
			const free = span - (col.length - 1) * PAD;
			let s =
				free /
				Math.max(
					1,
					col.reduce((t, n) => t + n.count, 0)
				);
			for (let pass = 0; pass < 3; pass++) {
				const small = col.filter((n) => n.count * s < MIN_NODE);
				const rest = col.reduce((t, n) => t + (n.count * s < MIN_NODE ? 0 : n.count), 0);
				if (!small.length || !rest) break;
				s = (free - small.length * MIN_NODE) / rest;
			}
			scale = Math.min(scale, s);
		}
		if (!Number.isFinite(scale)) scale = 1;
		const size = (n: Laid) => Math.max(MIN_NODE, n.count * scale);
		for (const [i, col] of cols.entries()) {
			col.sort((a, b) => b.count - a.count);
			const used = col.reduce((t, n) => t + size(n), 0) + (col.length - 1) * PAD;
			let y = inner.y0 + Math.max(0, (span - used) / 2);
			for (const n of col) {
				n.x0 = colX(i);
				n.x1 = n.x0 + NODE_W;
				n.y0 = y;
				n.y1 = y + size(n);
				y = n.y1 + PAD;
			}
		}
		const byId = new Map(nodes.map((n) => [n.id, n]));
		const sorted = flow.links
			.filter((l) => byId.has(l.source) && byId.has(l.target))
			.sort((a, b) => {
				const sa = byId.get(a.source)!;
				const sb = byId.get(b.source)!;
				const ta = byId.get(a.target)!;
				const tb = byId.get(b.target)!;
				return sa.y0 - sb.y0 || ta.y0 - tb.y0;
			});
		const outSum: Record<string, number> = {};
		const inSum: Record<string, number> = {};
		for (const l of sorted) {
			outSum[l.source] = (outSum[l.source] ?? 0) + l.count * scale;
			inSum[l.target] = (inSum[l.target] ?? 0) + l.count * scale;
		}
		for (const n of nodes) {
			n.outY = n.y0 + (n.y1 - n.y0 - (outSum[n.id] ?? 0)) / 2;
			n.inY = n.y0 + (n.y1 - n.y0 - (inSum[n.id] ?? 0)) / 2;
		}
		const links: LaidLink[] = [];
		for (const l of sorted) {
			const from = byId.get(l.source)!;
			const to = byId.get(l.target)!;
			const w = Math.max(1.5, l.count * scale);
			const ya = from.outY + w / 2;
			const yb = to.inY + w / 2;
			from.outY += w;
			to.inY += w;
			const xa = from.x1;
			const xb = to.x0;
			const xm = (xa + xb) / 2;
			const path = `M${xa},${ya} C${xm},${ya} ${xm},${yb} ${xb},${yb}`;
			const length = Math.hypot(xb - xa, yb - ya) * 1.15;
			links.push({ ...l, path, width: w, from, to, length });
		}
		return { nodes, links, colX };
	});

	function connected(id: string): Hover {
		const nodes = new SvelteSet([id]);
		const links = new SvelteSet<number>();
		const walk = (from: string, dir: 'down' | 'up') => {
			layout.links.forEach((l, i) => {
				if (dir === 'down' && l.source === from && !links.has(i)) {
					links.add(i);
					nodes.add(l.target);
					walk(l.target, 'down');
				}
				if (dir === 'up' && l.target === from && !links.has(i)) {
					links.add(i);
					nodes.add(l.source);
					walk(l.source, 'up');
				}
			});
		};
		walk(id, 'down');
		walk(id, 'up');
		return { nodes, links };
	}

	function clampTip(x: number, y: number) {
		const w = el?.clientWidth ?? width;
		return { x: x + TIP_W + 12 > w ? Math.max(0, x - TIP_W - 24) : x, y };
	}
	function place(e: MouseEvent) {
		if (!el) return { x: 0, y: 0 };
		const r = el.getBoundingClientRect();
		return clampTip(e.clientX - r.left + 12, e.clientY - r.top + 12);
	}
	function anchor(n: Laid) {
		const x = n.column === 0 ? n.x0 - LABEL_L + 8 : n.x1 + 16;
		return clampTip(x, n.y1 + 6);
	}
	const assets = (n: number) => `${n.toLocaleString()} ${n === 1 ? 'web asset' : 'web assets'}`;
	function nodeTip(n: Laid, at: { x: number; y: number }): Tip {
		const parts = [n.detail, assets(n.count)];
		if (n.id !== 'resolving') parts.push(`${share(n.count, flow.resolving)} of resolving`);
		return { ...at, title: n.label, sub: parts.filter(Boolean).join(' · '), query: n.query };
	}
	function hoverNode(e: MouseEvent, n: Laid) {
		hovered = connected(n.id);
		tip = nodeTip(n, place(e));
	}
	function focusNode(n: Laid) {
		hovered = connected(n.id);
		tip = nodeTip(n, anchor(n));
	}
	function hoverLink(e: MouseEvent, i: number, l: LaidLink) {
		hovered = { nodes: new SvelteSet([l.source, l.target]), links: new SvelteSet([i]) };
		tip = {
			...place(e),
			title: `${l.from.label} → ${l.to.label}`,
			sub: `${assets(l.count)} · ${share(l.count, l.from.count)} of ${l.from.label}`,
			query: l.query
		};
	}
	function move(e: MouseEvent) {
		if (tip) tip = { ...tip, ...place(e) };
	}
	function leave() {
		hovered = null;
		tip = null;
	}
	function pick(query: string | null) {
		if (query) onPick(query);
	}
	function key(e: KeyboardEvent, query: string | null) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			pick(query);
		}
	}

	onMount(() => {
		if (!el) return;
		width = el.clientWidth;
		const ro = new ResizeObserver(() => {
			if (el) width = el.clientWidth;
		});
		ro.observe(el);
		reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
		let io: IntersectionObserver | null = null;
		if (reduce || !('IntersectionObserver' in window)) drawn = true;
		else {
			io = new IntersectionObserver(
				(entries) => {
					if (entries.some((x) => x.isIntersecting)) {
						drawn = true;
						io?.disconnect();
					}
				},
				{ threshold: 0.35 }
			);
			io.observe(el);
		}
		return () => {
			ro.disconnect();
			io?.disconnect();
		};
	});
</script>

<div bind:this={el} class="relative w-full">
	<svg
		viewBox="0 0 {width} {height}"
		{width}
		{height}
		class="block h-auto w-full overflow-visible"
		onmouseleave={leave}
		role="presentation"
	>
		{#each COLUMNS as c, i (c)}
			<text
				x={i === 0 ? layout.colX(0) + NODE_W : layout.colX(i)}
				y="11"
				text-anchor={i === 0 ? 'end' : 'start'}
				class="fill-muted-foreground text-[11px] font-semibold tracking-[0.08em] uppercase"
			>
				{c}
			</text>
		{/each}

		{#each layout.links as l, i (`${l.source}-${l.target}`)}
			{@const on = hovered ? hovered.links.has(i) : true}
			<g
				class="link {l.query ? 'cursor-pointer' : ''}"
				role="button"
				tabindex="-1"
				aria-label="{l.from.label} to {l.to.label}, {assets(l.count)}"
				onmouseenter={(e) => hoverLink(e, i, l)}
				onmousemove={move}
				onclick={() => pick(l.query)}
				onkeydown={(e) => key(e, l.query)}
			>
				<path
					d={l.path}
					fill="none"
					stroke={FILL[l.from.tone] ?? FILL.muted}
					stroke-width={l.width}
					style="opacity:{hovered
						? on
							? 0.7
							: 0.08
						: 0.32};stroke-dasharray:{l.length} {l.length};stroke-dashoffset:{drawn
						? 0
						: l.length};transition:stroke-dashoffset 650ms cubic-bezier(.33,1,.68,1) {120 +
						l.from.column * 360}ms,opacity 150ms"
				/>
				{#if hovered && on && !reduce}
					<path
						d={l.path}
						fill="none"
						stroke="var(--background)"
						stroke-width={l.width}
						class="flowing pointer-events-none"
					/>
				{/if}
				<path
					d={l.path}
					fill="none"
					stroke="transparent"
					stroke-width={Math.max(l.width, HIT_MIN)}
				/>
			</g>
		{/each}

		{#each layout.nodes as n (n.id)}
			{@const on = hovered ? hovered.nodes.has(n.id) : true}
			{@const left = n.column === 0}
			<g
				class="node {n.query ? 'cursor-pointer' : ''}"
				role="button"
				tabindex={n.query ? 0 : -1}
				aria-label="{n.label}, {assets(n.count)}"
				style="opacity:{drawn ? (on ? 1 : 0.3) : 0};transition:opacity 300ms {60 +
					n.column * 360}ms"
				onmouseenter={(e) => hoverNode(e, n)}
				onmousemove={move}
				onfocus={() => focusNode(n)}
				onblur={leave}
				onclick={() => pick(n.query)}
				onkeydown={(e) => key(e, n.query)}
			>
				<rect
					x={left ? n.x0 - LABEL_L : n.x0}
					y={Math.min(n.y0, (n.y0 + n.y1) / 2 - 10)}
					width={left ? LABEL_L + NODE_W : NODE_W + LABEL_R}
					height={Math.max(n.y1 - n.y0, 20)}
					fill="transparent"
				/>
				<rect
					class="bar"
					x={n.x0}
					y={n.y0}
					width={NODE_W}
					height={n.y1 - n.y0}
					rx="2"
					fill={FILL[n.tone] ?? FILL.muted}
				/>
				<text
					x={left ? n.x0 - 8 : n.x1 + 8}
					y={(n.y0 + n.y1) / 2}
					dy="0.35em"
					text-anchor={left ? 'end' : 'start'}
					class="pointer-events-none text-[12px] {n.tone === 'muted'
						? 'fill-muted-foreground'
						: 'fill-foreground'} {on && hovered ? 'font-medium' : ''}"
					style="paint-order:stroke;stroke:var(--flow-halo, var(--card));stroke-width:3px;stroke-linejoin:round"
				>
					{clip(n.label)}
					<tspan dx="6" class="fill-muted-foreground tabular-nums">{n.count.toLocaleString()}</tspan
					>
				</text>
			</g>
		{/each}
	</svg>

	{#if tip}
		<div
			class="pointer-events-none absolute z-10 w-72 max-w-full rounded-md border bg-popover px-2.5 py-2 text-xs text-popover-foreground shadow-md"
			style="left:{tip.x}px;top:{tip.y}px"
		>
			<div class="font-medium">{tip.title}</div>
			<div class="text-muted-foreground">{tip.sub}</div>
			{#if tip.query}
				<div class="mt-1.5 flex items-center justify-between gap-3 border-t pt-1.5">
					<code class="truncate font-mono text-[11px] text-primary">{tip.query}</code>
					<span class="flex shrink-0 items-center gap-0.5 text-muted-foreground">
						Web Assets <ArrowUpRight class="size-3" />
					</span>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.node:focus,
	.link:focus {
		outline: none;
	}
	.node:focus-visible .bar {
		stroke: var(--ring);
		stroke-width: 2px;
	}
	.node:hover .bar {
		stroke: var(--foreground);
		stroke-opacity: 0.35;
		stroke-width: 1.5px;
	}
	.flowing {
		opacity: 0.18;
		stroke-dasharray: 6 30;
		animation: flow 1.1s linear infinite;
	}
	@keyframes flow {
		from {
			stroke-dashoffset: 36;
		}
		to {
			stroke-dashoffset: 0;
		}
	}
</style>
