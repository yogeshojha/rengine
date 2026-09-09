<script lang="ts" module>
	export interface GraphNode {
		id: string;
		kind: 'hub' | 'host';
		label: string;
		r: number;
		hub?: CorrelationHub;
		host?: CorrelationHost;
		hostIndex?: number;
		x: number;
		y: number;
		vx?: number;
		vy?: number;
		fx?: number | null;
		fy?: number | null;
	}
	export interface GraphLink {
		source: GraphNode;
		target: GraphNode;
		kind: string;
	}
</script>

<script lang="ts">
	import { untrack } from 'svelte';
	import {
		forceCenter,
		forceCollide,
		forceLink,
		forceManyBody,
		forceSimulation,
		forceX,
		forceY,
		type Simulation
	} from 'd3-force';
	import Plus from '@lucide/svelte/icons/plus';
	import Minus from '@lucide/svelte/icons/minus';
	import Maximize from '@lucide/svelte/icons/maximize';
	import Shuffle from '@lucide/svelte/icons/shuffle';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import { KIND_COLOR_VAR, KIND_DASHED, MAX_ZOOM, MIN_ZOOM } from '$lib/config/correlation';
	import type { CorrelationHost, CorrelationHub } from '$lib/types/correlation';

	interface Props {
		hosts: CorrelationHost[];
		hubs: CorrelationHub[];
		height?: number;
		selectedId?: string | null;
		onSelect: (node: GraphNode | null) => void;
		onOpen?: (node: GraphNode) => void;
		class?: string;
	}

	let {
		hosts,
		hubs,
		height = 560,
		selectedId = null,
		onSelect,
		onOpen,
		class: className = ''
	}: Props = $props();

	const HOST_R = 3.5;
	const HUB_MIN_R = 7;
	const HUB_MAX_R = 26;
	const LABEL_ZOOM = 1.6;
	const HIT_PAD = 6;
	const SETTLE_TICKS = 300;
	const FIT_PAD = 40;

	let canvas = $state<HTMLCanvasElement | null>(null);
	let width = $state(0);
	let hovered = $state<GraphNode | null>(null);
	let pointer = $state({ x: 0, y: 0 });
	let nodes: GraphNode[] = [];
	let links: GraphLink[] = [];
	let simulation: Simulation<GraphNode, undefined> | null = null;
	let transform = $state({ k: 1, x: 0, y: 0 });
	let frame = 0;
	let drag: {
		node: GraphNode | null;
		sx: number;
		sy: number;
		ox: number;
		oy: number;
		moved: boolean;
	} | null = null;
	let previous = new Map<string, { x: number; y: number }>();
	let colors: Record<string, string> = {};
	let reduced = false;

	function readColors() {
		const style = getComputedStyle(document.documentElement);
		const read = (name: string) => style.getPropertyValue(name).trim();
		colors = {
			card: read('--card'),
			ink: read('--foreground'),
			muted: read('--muted-foreground'),
			border: read('--border'),
			primary: read('--primary')
		};
		for (const v of new Set(Object.values(KIND_COLOR_VAR))) colors[v] = read(v);
	}
	const kindColor = (kind: string) =>
		colors[KIND_COLOR_VAR[kind] ?? '--muted-foreground'] ?? '#888';

	function hubRadius(count: number, max: number): number {
		const t = Math.sqrt(count / Math.max(1, max));
		return HUB_MIN_R + t * (HUB_MAX_R - HUB_MIN_R);
	}

	// a node keeps its place across rebuilds so toggling a kind moves only what changed
	function build() {
		const maxCount = Math.max(1, ...hubs.map((h) => h.count));
		const used = new Set(hubs.flatMap((h) => h.members));
		const next: GraphNode[] = [];
		const cx = width / 2;
		const cy = height / 2;
		const seed = (id: string, i: number) => {
			const p = previous.get(id);
			if (p) return p;
			const a = (i * 2.399963) % (Math.PI * 2);
			const d = 20 + Math.sqrt(i) * 14;
			return { x: cx + Math.cos(a) * d, y: cy + Math.sin(a) * d };
		};
		let i = 0;
		for (const hub of hubs) {
			const id = `hub:${hub.id}`;
			next.push({
				id,
				kind: 'hub',
				label: hub.label,
				r: hubRadius(hub.count, maxCount),
				hub,
				...seed(id, i++)
			});
		}
		const hostNodes = new Map(
			[...used]
				.filter((index) => hosts[index])
				.map((index): [number, GraphNode] => {
					const host = hosts[index];
					const id = `host:${host.id}`;
					return [
						index,
						{
							id,
							kind: 'host',
							label: host.name,
							r: HOST_R,
							host,
							hostIndex: index,
							...seed(id, i++)
						}
					];
				})
		);
		next.push(...hostNodes.values());
		const byId = new Map(next.map((n) => [n.id, n]));
		const nextLinks: GraphLink[] = [];
		for (const hub of hubs) {
			const source = byId.get(`hub:${hub.id}`)!;
			for (const index of hub.members) {
				const target = hostNodes.get(index);
				if (target) nextLinks.push({ source, target, kind: hub.kind });
			}
		}
		nodes = next;
		links = nextLinks;
		simulation?.stop();
		simulation = forceSimulation<GraphNode>(nodes)
			.force(
				'link',
				forceLink<GraphNode, GraphLink>(links)
					.distance((l) => 18 + l.source.r)
					.strength(0.6)
			)
			.force(
				'charge',
				forceManyBody<GraphNode>().strength((n) => (n.kind === 'hub' ? -220 : -18))
			)
			.force(
				'collide',
				forceCollide<GraphNode>().radius((n) => n.r + 3)
			)
			.force('x', forceX(cx).strength(0.03))
			.force('y', forceY(cy).strength(0.03))
			.force('center', forceCenter(cx, cy).strength(0.02))
			.alpha(1)
			.alphaDecay(reduced ? 1 : 0.03);
		if (reduced) {
			simulation.stop();
			simulation.tick(SETTLE_TICKS);
			fit();
			draw();
		} else {
			// the view follows the layout as it settles, the way the globe draws in
			simulation.on('tick', fit).on('end', () => {
				remember();
				fit();
			});
		}
	}

	function remember() {
		previous = new Map(nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
	}

	function schedule() {
		if (!frame) frame = requestAnimationFrame(draw);
	}

	function fit() {
		if (!nodes.length || !width) return;
		let minX = Infinity;
		let minY = Infinity;
		let maxX = -Infinity;
		let maxY = -Infinity;
		for (const n of nodes) {
			minX = Math.min(minX, n.x - n.r);
			minY = Math.min(minY, n.y - n.r);
			maxX = Math.max(maxX, n.x + n.r);
			maxY = Math.max(maxY, n.y + n.r);
		}
		const w = Math.max(1, maxX - minX);
		const h = Math.max(1, maxY - minY);
		const k = Math.min(
			MAX_ZOOM,
			Math.max(MIN_ZOOM, Math.min((width - FIT_PAD * 2) / w, (height - FIT_PAD * 2) / h))
		);
		transform = {
			k,
			x: width / 2 - ((minX + maxX) / 2) * k,
			y: height / 2 - ((minY + maxY) / 2) * k
		};
		schedule();
	}

	function neighbours(node: GraphNode | null): Set<string> {
		if (!node) return new Set();
		return new Set([
			node.id,
			...links
				.filter((l) => l.source.id === node.id || l.target.id === node.id)
				.map((l) => (l.source.id === node.id ? l.target.id : l.source.id))
		]);
	}

	function draw() {
		frame = 0;
		const el = canvas;
		if (!el || !width) return;
		const dpr = window.devicePixelRatio || 1;
		if (el.width !== Math.round(width * dpr) || el.height !== Math.round(height * dpr)) {
			el.width = Math.round(width * dpr);
			el.height = Math.round(height * dpr);
		}
		const ctx = el.getContext('2d');
		if (!ctx) return;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, width, height);
		ctx.translate(transform.x, transform.y);
		ctx.scale(transform.k, transform.k);
		const k = transform.k;
		const focus = hovered ?? nodes.find((n) => n.id === selectedId) ?? null;
		const lit = neighbours(focus);
		const dim = focus !== null;

		ctx.lineWidth = 1 / k;
		for (const l of links) {
			const on = !dim || (lit.has(l.source.id) && lit.has(l.target.id));
			ctx.globalAlpha = on ? (dim ? 0.55 : 0.22) : 0.04;
			ctx.strokeStyle = kindColor(l.kind);
			ctx.beginPath();
			ctx.moveTo(l.source.x, l.source.y);
			ctx.lineTo(l.target.x, l.target.y);
			ctx.stroke();
		}

		for (const n of nodes) {
			const on = !dim || lit.has(n.id);
			ctx.globalAlpha = on ? 1 : 0.12;
			if (n.kind === 'host') {
				const live = n.host?.live;
				ctx.beginPath();
				ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
				ctx.fillStyle = live ? colors.ink : colors.card;
				ctx.fill();
				ctx.lineWidth = 1.2 / k;
				ctx.strokeStyle = live ? colors.card : colors.muted;
				ctx.stroke();
			} else if (n.hub) {
				const color = kindColor(n.hub.kind);
				ctx.beginPath();
				ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
				ctx.fillStyle = color;
				ctx.globalAlpha = (on ? 1 : 0.12) * (n.hub.common ? 0.45 : 0.9);
				ctx.fill();
				ctx.globalAlpha = on ? 1 : 0.12;
				ctx.lineWidth = 2 / k;
				ctx.strokeStyle = colors.card;
				ctx.setLineDash(KIND_DASHED.has(n.hub.kind) ? [3 / k, 3 / k] : []);
				ctx.stroke();
				ctx.setLineDash([]);
				if (n.id === selectedId) {
					ctx.beginPath();
					ctx.arc(n.x, n.y, n.r + 4 / k, 0, Math.PI * 2);
					ctx.lineWidth = 2 / k;
					ctx.strokeStyle = colors.primary;
					ctx.stroke();
				}
			}
		}

		ctx.font = `${11 / k}px ui-sans-serif, system-ui, sans-serif`;
		ctx.textBaseline = 'middle';
		for (const n of nodes) {
			const on = !dim || lit.has(n.id);
			const showHost = n.kind === 'host' && (k >= LABEL_ZOOM || n.id === focus?.id);
			const showHub = n.kind === 'hub' && (on || k >= LABEL_ZOOM);
			if (!showHost && !showHub) continue;
			ctx.globalAlpha = on ? 1 : 0.2;
			const text = n.label.length > 28 ? `${n.label.slice(0, 27)}…` : n.label;
			const x = n.x + n.r + 4 / k;
			const metrics = ctx.measureText(text);
			ctx.fillStyle = colors.card;
			ctx.globalAlpha = (on ? 1 : 0.2) * 0.85;
			ctx.fillRect(x - 2 / k, n.y - 7 / k, metrics.width + 4 / k, 14 / k);
			ctx.globalAlpha = on ? 1 : 0.2;
			ctx.fillStyle = n.kind === 'hub' ? colors.ink : colors.muted;
			ctx.fillText(text, x, n.y);
		}
		ctx.globalAlpha = 1;
	}

	function toGraph(e: PointerEvent | WheelEvent): { x: number; y: number } {
		const rect = canvas!.getBoundingClientRect();
		const px = e.clientX - rect.left;
		const py = e.clientY - rect.top;
		return { x: (px - transform.x) / transform.k, y: (py - transform.y) / transform.k };
	}
	function nodeAt(p: { x: number; y: number }): GraphNode | null {
		let best: GraphNode | null = null;
		let bestD = Infinity;
		const pad = HIT_PAD / transform.k;
		for (const n of nodes) {
			const dx = n.x - p.x;
			const dy = n.y - p.y;
			const d = Math.sqrt(dx * dx + dy * dy) - n.r;
			if (d <= pad && d < bestD) {
				best = n;
				bestD = d;
			}
		}
		return best;
	}

	function onPointerDown(e: PointerEvent) {
		if (!canvas) return;
		canvas.setPointerCapture(e.pointerId);
		const p = toGraph(e);
		const node = nodeAt(p);
		drag = { node, sx: e.clientX, sy: e.clientY, ox: transform.x, oy: transform.y, moved: false };
		if (node) {
			node.fx = node.x;
			node.fy = node.y;
			simulation?.alphaTarget(0.25).restart();
		}
	}
	function onPointerMove(e: PointerEvent) {
		const rect = canvas?.getBoundingClientRect();
		pointer = { x: e.clientX - (rect?.left ?? 0), y: e.clientY - (rect?.top ?? 0) };
		if (drag) {
			const dx = e.clientX - drag.sx;
			const dy = e.clientY - drag.sy;
			if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
			if (drag.node) {
				const p = toGraph(e);
				drag.node.fx = p.x;
				drag.node.fy = p.y;
				if (reduced) {
					drag.node.x = p.x;
					drag.node.y = p.y;
					schedule();
				}
			} else {
				transform = { ...transform, x: drag.ox + dx, y: drag.oy + dy };
				schedule();
			}
			return;
		}
		const node = nodeAt(toGraph(e));
		if (node !== hovered) {
			hovered = node;
			schedule();
		}
	}
	function onPointerUp(e: PointerEvent) {
		if (!drag) return;
		const { node, moved } = drag;
		drag = null;
		if (node) {
			node.fx = null;
			node.fy = null;
			simulation?.alphaTarget(0);
			if (!moved) onSelect(node.id === selectedId ? null : node);
		} else if (!moved) {
			onSelect(null);
		}
		if (!moved) schedule();
		void e;
	}
	function onPointerLeave() {
		hovered = null;
		schedule();
	}
	function onWheel(e: WheelEvent) {
		e.preventDefault();
		const rect = canvas!.getBoundingClientRect();
		const px = e.clientX - rect.left;
		const py = e.clientY - rect.top;
		const factor = Math.exp(-e.deltaY * 0.0015);
		zoomAt(factor, px, py);
	}
	function zoomAt(factor: number, px: number, py: number) {
		const k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, transform.k * factor));
		const ratio = k / transform.k;
		transform = { k, x: px - (px - transform.x) * ratio, y: py - (py - transform.y) * ratio };
		schedule();
	}
	function onDoubleClick(e: MouseEvent) {
		const node = hovered;
		if (node && onOpen) {
			e.preventDefault();
			onOpen(node);
		}
	}
	function relayout() {
		previous = new Map();
		build();
	}
	export function focusNode(id: string) {
		const node = nodes.find((n) => n.id === id);
		if (!node) return;
		const k = Math.max(transform.k, 1.2);
		transform = { k, x: width / 2 - node.x * k, y: height / 2 - node.y * k };
		schedule();
	}

	$effect(() => {
		readColors();
		reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		const observer = new MutationObserver(() => {
			readColors();
			schedule();
		});
		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class', 'data-theme']
		});
		return () => {
			observer.disconnect();
			simulation?.stop();
			if (frame) cancelAnimationFrame(frame);
		};
	});

	let inputKey = $derived(`${hubs.map((h) => h.id).join('|')}#${hosts.length}`);
	let builtKey = '';
	$effect(() => {
		void inputKey;
		void width;
		if (!width) return;
		untrack(() => {
			if (inputKey === builtKey) {
				schedule();
				return;
			}
			builtKey = inputKey;
			remember();
			build();
		});
	});
	$effect(() => {
		void selectedId;
		schedule();
	});

	let tip = $derived.by(() => {
		const n = hovered;
		if (!n) return null;
		if (n.kind === 'hub' && n.hub)
			return {
				title: n.hub.value,
				lines: [
					`${n.hub.count.toLocaleString()} hosts share this`,
					n.hub.common ? 'Common across the estate' : ''
				]
			};
		if (n.host)
			return {
				title: n.host.name,
				lines: [
					n.host.status !== null ? `HTTP ${n.host.status}` : 'Did not answer',
					n.host.title ?? '',
					`${n.host.hubs} shared ${n.host.hubs === 1 ? 'identity' : 'identities'}`
				]
			};
		return null;
	});
</script>

<div class="relative {className}" bind:clientWidth={width} style="height:{height}px">
	<canvas
		bind:this={canvas}
		class="block size-full touch-none {hovered ? 'cursor-pointer' : 'cursor-grab'}"
		style="width:{width}px;height:{height}px"
		onpointerdown={onPointerDown}
		onpointermove={onPointerMove}
		onpointerup={onPointerUp}
		onpointercancel={onPointerUp}
		onpointerleave={onPointerLeave}
		onwheel={onWheel}
		ondblclick={onDoubleClick}
		aria-label="Hosts connected by the identities they share"
	></canvas>

	{#if tip}
		<div
			class="pointer-events-none absolute z-10 max-w-72 rounded-md border bg-popover px-2.5 py-1.5 text-xs shadow-md"
			style="left:{Math.min(pointer.x + 14, Math.max(0, width - 300))}px;top:{pointer.y + 14}px"
		>
			<p class="truncate font-mono font-medium">{tip.title}</p>
			{#each tip.lines.filter(Boolean) as line (line)}
				<p class="text-muted-foreground">{line}</p>
			{/each}
		</div>
	{/if}

	<div class="absolute right-3 bottom-3 flex flex-col gap-1">
		<Hint text="Zoom in">
			{#snippet child(props)}
				<Button
					{...props}
					variant="outline"
					size="icon"
					class="size-7 bg-card"
					onclick={() => zoomAt(1.4, width / 2, height / 2)}
				>
					<Plus class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
		<Hint text="Zoom out">
			{#snippet child(props)}
				<Button
					{...props}
					variant="outline"
					size="icon"
					class="size-7 bg-card"
					onclick={() => zoomAt(1 / 1.4, width / 2, height / 2)}
				>
					<Minus class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
		<Hint text="Fit to view">
			{#snippet child(props)}
				<Button {...props} variant="outline" size="icon" class="size-7 bg-card" onclick={fit}>
					<Maximize class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
		<Hint text="Lay out again">
			{#snippet child(props)}
				<Button {...props} variant="outline" size="icon" class="size-7 bg-card" onclick={relayout}>
					<Shuffle class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
	</div>
</div>
