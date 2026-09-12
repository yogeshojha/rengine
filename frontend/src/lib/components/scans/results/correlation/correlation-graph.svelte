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
		born: number;
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
	import { KIND_DASHED, MAX_ZOOM, MIN_ZOOM, kindColor } from '$lib/config/correlation';
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

	const HOST_R = 3.2;
	const HUB_MIN_R = 8;
	const HUB_MAX_R = 26;
	const LABEL_ZOOM = 1.4;
	const LABEL_MIN_COUNT = 3;
	const HIT_PAD = 6;
	const SETTLE_TICKS = 300;
	const FIT_PAD = 48;
	const GRID = 24;
	const BLOB_PAD = 14;
	const POP_MS = 420;

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
	let colors = { card: '#fff', ink: '#111', muted: '#888', border: '#ddd', primary: '#55f' };
	let dark = false;
	let font = 'ui-sans-serif, system-ui, sans-serif';
	let reduced = false;

	function readTheme() {
		const root = document.documentElement;
		const style = getComputedStyle(root);
		const read = (name: string) => style.getPropertyValue(name).trim();
		colors = {
			card: read('--card'),
			ink: read('--foreground'),
			muted: read('--muted-foreground'),
			border: read('--border'),
			primary: read('--primary')
		};
		dark = root.classList.contains('dark');
		font = getComputedStyle(document.body).fontFamily || font;
	}
	const tone = (kind: string, alpha = 1) => kindColor(kind, dark, alpha);
	const ease = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

	function hubRadius(count: number, max: number): number {
		const t = Math.sqrt(count / Math.max(1, max));
		return HUB_MIN_R + t * (HUB_MAX_R - HUB_MIN_R);
	}

	// keep positions across rebuilds
	function build() {
		const maxCount = Math.max(1, ...hubs.map((h) => h.count));
		const used = new Set(hubs.flatMap((h) => h.members));
		const next: GraphNode[] = [];
		const cx = width / 2;
		const cy = height / 2;
		const now = performance.now();
		const seed = (id: string, i: number) => {
			const p = previous.get(id);
			if (p) return { ...p, born: now - POP_MS };
			const a = (i * 2.399963) % (Math.PI * 2);
			const d = 20 + Math.sqrt(i) * 14;
			return { x: cx + Math.cos(a) * d, y: cy + Math.sin(a) * d, born: now + i * 6 };
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
					.distance((l) => 22 + l.source.r)
					.strength(0.6)
			)
			.force(
				'charge',
				forceManyBody<GraphNode>().strength((n) => (n.kind === 'hub' ? -260 : -22))
			)
			.force(
				'collide',
				forceCollide<GraphNode>().radius((n) => n.r + 4)
			)
			.force('x', forceX(cx).strength(0.03))
			.force('y', forceY(cy).strength(0.03))
			.force('center', forceCenter(cx, cy).strength(0.02))
			.alpha(1)
			.alphaDecay(reduced ? 1 : 0.03);
		if (reduced) {
			simulation.stop();
			simulation.tick(SETTLE_TICKS);
			for (const n of nodes) n.born = 0;
			fit();
			draw();
		} else {
			// fit on every tick while settling
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

	type Point = { x: number; y: number };
	// convex hull, monotone chain
	function hull(points: Point[]): Point[] {
		const pts = [...points].sort((a, b) => a.x - b.x || a.y - b.y);
		if (pts.length < 3) return pts;
		const cross = (o: Point, a: Point, b: Point) =>
			(a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
		const lower: Point[] = [];
		for (const p of pts) {
			while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0)
				lower.pop();
			lower.push(p);
		}
		const upper: Point[] = [];
		for (const p of [...pts].reverse()) {
			while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0)
				upper.pop();
			upper.push(p);
		}
		return [...lower.slice(0, -1), ...upper.slice(0, -1)];
	}

	function roundRect(
		ctx: CanvasRenderingContext2D,
		x: number,
		y: number,
		w: number,
		h: number,
		r: number
	) {
		ctx.beginPath();
		ctx.moveTo(x + r, y);
		ctx.arcTo(x + w, y, x + w, y + h, r);
		ctx.arcTo(x + w, y + h, x, y + h, r);
		ctx.arcTo(x, y + h, x, y, r);
		ctx.arcTo(x, y, x + w, y, r);
		ctx.closePath();
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
		const now = performance.now();
		let animating = false;
		const grow = (n: GraphNode) => {
			const t = (now - n.born) / POP_MS;
			if (t < 1) animating = true;
			return ease(t);
		};

		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, width, height);

		// dot grid
		const step = GRID * transform.k;
		if (step >= 10) {
			ctx.fillStyle = colors.muted;
			ctx.globalAlpha = dark ? 0.22 : 0.28;
			const ox = ((transform.x % step) + step) % step;
			const oy = ((transform.y % step) + step) % step;
			for (let gx = ox; gx < width; gx += step)
				for (let gy = oy; gy < height; gy += step) ctx.fillRect(gx - 0.5, gy - 0.5, 1, 1);
			ctx.globalAlpha = 1;
		}

		ctx.translate(transform.x, transform.y);
		ctx.scale(transform.k, transform.k);
		const k = transform.k;
		const focus = hovered ?? nodes.find((n) => n.id === selectedId) ?? null;
		const lit = neighbours(focus);
		const dim = focus !== null;
		const memberNodes: Record<string, GraphNode[]> = {};
		for (const l of links) (memberNodes[l.source.id] ??= []).push(l.target);

		// cluster washes
		ctx.lineJoin = 'round';
		ctx.lineCap = 'round';
		for (const n of nodes) {
			if (n.kind !== 'hub' || !n.hub) continue;
			const members = memberNodes[n.id] ?? [];
			if (!members.length) continue;
			const on = !dim || lit.has(n.id);
			const outline = hull([n, ...members]);
			ctx.globalAlpha = (on ? (dim ? 0.16 : 0.09) : 0.03) * grow(n);
			ctx.fillStyle = tone(n.hub.kind);
			ctx.strokeStyle = tone(n.hub.kind);
			ctx.lineWidth = (BLOB_PAD + n.r) * 2;
			ctx.beginPath();
			outline.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
			ctx.closePath();
			ctx.stroke();
			if (outline.length >= 3) ctx.fill();
		}

		// links
		for (const l of links) {
			const on = !dim || (lit.has(l.source.id) && lit.has(l.target.id));
			const g = Math.min(grow(l.source), grow(l.target));
			ctx.globalAlpha = (on ? (dim ? 0.7 : 0.28) : 0.05) * g;
			ctx.strokeStyle = tone(l.kind);
			ctx.lineWidth = (on && dim ? 1.4 : 1) / k;
			const mx = (l.source.x + l.target.x) / 2;
			const my = (l.source.y + l.target.y) / 2;
			const dx = l.target.x - l.source.x;
			const dy = l.target.y - l.source.y;
			const bend = 0.12 * (l.target.id.charCodeAt(6) % 2 ? 1 : -1);
			ctx.beginPath();
			ctx.moveTo(l.source.x, l.source.y);
			ctx.quadraticCurveTo(mx - dy * bend, my + dx * bend, l.target.x, l.target.y);
			ctx.stroke();
		}

		// hosts
		for (const n of nodes) {
			if (n.kind !== 'host') continue;
			const on = !dim || lit.has(n.id);
			const g = grow(n);
			const r = n.r * g;
			const live = !!n.host?.live;
			ctx.globalAlpha = (on ? 1 : 0.15) * g;
			if (live) {
				ctx.shadowColor = colors.ink;
				ctx.shadowBlur = 6 / k;
			}
			ctx.beginPath();
			ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
			ctx.fillStyle = live ? colors.ink : colors.card;
			ctx.fill();
			ctx.shadowBlur = 0;
			ctx.lineWidth = 1.2 / k;
			ctx.strokeStyle = live ? colors.card : colors.muted;
			ctx.stroke();
		}

		// hubs
		for (const n of nodes) {
			if (n.kind !== 'hub' || !n.hub) continue;
			const on = !dim || lit.has(n.id);
			const g = grow(n);
			const hot = n.id === focus?.id;
			const r = n.r * g * (hot ? 1.08 : 1);
			const color = tone(n.hub.kind);
			const fade = n.hub.common ? 0.55 : 1;
			ctx.globalAlpha = (on ? 1 : 0.12) * g * fade;

			ctx.shadowColor = tone(n.hub.kind, dark ? 0.55 : 0.4);
			ctx.shadowBlur = (hot ? 28 : 16) / k;
			ctx.beginPath();
			ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
			ctx.fillStyle = tone(n.hub.kind, dark ? 0.28 : 0.2);
			ctx.fill();
			ctx.shadowBlur = 0;

			const core = ctx.createRadialGradient(n.x - r * 0.3, n.y - r * 0.35, r * 0.1, n.x, n.y, r);
			core.addColorStop(0, tone(n.hub.kind, dark ? 0.75 : 0.55));
			core.addColorStop(1, tone(n.hub.kind, dark ? 0.22 : 0.16));
			ctx.beginPath();
			ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
			ctx.fillStyle = core;
			ctx.fill();

			ctx.lineWidth = 1.5 / k;
			ctx.strokeStyle = color;
			ctx.setLineDash(KIND_DASHED.has(n.hub.kind) ? [3 / k, 3 / k] : []);
			ctx.stroke();
			ctx.setLineDash([]);

			ctx.beginPath();
			ctx.arc(n.x, n.y, Math.max(2, r * 0.22), 0, Math.PI * 2);
			ctx.fillStyle = color;
			ctx.fill();

			if (n.id === selectedId) {
				ctx.beginPath();
				ctx.arc(n.x, n.y, r + 5 / k, 0, Math.PI * 2);
				ctx.lineWidth = 1.5 / k;
				ctx.strokeStyle = colors.primary;
				ctx.setLineDash([4 / k, 3 / k]);
				ctx.stroke();
				ctx.setLineDash([]);
			}
		}

		// labels
		ctx.font = `500 ${11 / k}px ${font}`;
		ctx.textBaseline = 'middle';
		for (const n of nodes) {
			const on = !dim || lit.has(n.id);
			const isFocus = n.id === focus?.id;
			const showHost = n.kind === 'host' && (k >= LABEL_ZOOM || isFocus || (dim && on));
			const showHub =
				n.kind === 'hub' &&
				((n.hub?.count ?? 0) >= LABEL_MIN_COUNT || k >= LABEL_ZOOM || isFocus || (dim && on));
			if (!showHost && !showHub) continue;
			const g = grow(n);
			const text = n.label.length > 30 ? `${n.label.slice(0, 29)}…` : n.label;
			const w = ctx.measureText(text).width;
			const padX = 6 / k;
			const h = 18 / k;
			const x = n.x + n.r + 6 / k;
			const y = n.y - h / 2;
			ctx.globalAlpha = (on ? 1 : 0.2) * g;
			roundRect(ctx, x, y, w + padX * 2 + (n.kind === 'hub' ? 10 / k : 0), h, 6 / k);
			ctx.fillStyle = colors.card;
			ctx.fill();
			ctx.lineWidth = 1 / k;
			ctx.strokeStyle = n.kind === 'hub' && n.hub ? tone(n.hub.kind, 0.45) : colors.border;
			ctx.stroke();
			let tx = x + padX;
			if (n.kind === 'hub' && n.hub) {
				ctx.beginPath();
				ctx.arc(tx + 3 / k, n.y, 3 / k, 0, Math.PI * 2);
				ctx.fillStyle = tone(n.hub.kind);
				ctx.fill();
				tx += 10 / k;
			}
			ctx.fillStyle = n.kind === 'hub' ? colors.ink : colors.muted;
			ctx.fillText(text, tx, n.y);
		}
		ctx.globalAlpha = 1;
		if (animating) schedule();
	}

	function toGraph(e: PointerEvent | WheelEvent): Point {
		const rect = canvas!.getBoundingClientRect();
		const px = e.clientX - rect.left;
		const py = e.clientY - rect.top;
		return { x: (px - transform.x) / transform.k, y: (py - transform.y) / transform.k };
	}
	function nodeAt(p: Point): GraphNode | null {
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
		const node = nodeAt(toGraph(e));
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
	function onPointerUp() {
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
	}
	function onPointerLeave() {
		hovered = null;
		schedule();
	}
	function onWheel(e: WheelEvent) {
		e.preventDefault();
		const rect = canvas!.getBoundingClientRect();
		zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - rect.left, e.clientY - rect.top);
	}
	function zoomAt(factor: number, px: number, py: number) {
		const k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, transform.k * factor));
		const ratio = k / transform.k;
		transform = { k, x: px - (px - transform.x) * ratio, y: py - (py - transform.y) * ratio };
		schedule();
	}
	function onDoubleClick(e: MouseEvent) {
		if (hovered && onOpen) {
			e.preventDefault();
			onOpen(hovered);
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
		readTheme();
		reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		const observer = new MutationObserver(() => {
			readTheme();
			schedule();
		});
		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class', 'data-theme', 'style']
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
				kind: n.hub.kind,
				title: n.hub.value,
				lines: [
					`Shared by ${n.hub.count.toLocaleString()} web assets`,
					n.hub.common ? 'Common in this scan' : ''
				]
			};
		if (n.host)
			return {
				kind: null,
				title: n.host.name,
				lines: [
					n.host.status !== null ? `HTTP ${n.host.status}` : 'No HTTP response',
					n.host.title ?? '',
					`${n.host.hubs} shared ${n.host.hubs === 1 ? 'identity' : 'identities'}`
				]
			};
		return null;
	});
</script>

<div class="relative bg-muted/20 {className}" bind:clientWidth={width} style="height:{height}px">
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
		aria-label="Web assets grouped by shared identity"
	></canvas>

	{#if tip}
		<div
			class="pointer-events-none absolute z-10 max-w-72 rounded-lg border bg-popover/95 px-3 py-2 text-xs shadow-lg backdrop-blur"
			style="left:{Math.min(pointer.x + 14, Math.max(0, width - 300))}px;top:{pointer.y + 14}px"
		>
			<p class="flex items-center gap-1.5 font-mono font-medium">
				{#if tip.kind}
					<span class="size-2 shrink-0 rounded-full" style="background:{tone(tip.kind)}"></span>
				{/if}
				<span class="truncate">{tip.title}</span>
			</p>
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
					class="size-7 bg-card/90 backdrop-blur"
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
					class="size-7 bg-card/90 backdrop-blur"
					onclick={() => zoomAt(1 / 1.4, width / 2, height / 2)}
				>
					<Minus class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
		<Hint text="Fit to view">
			{#snippet child(props)}
				<Button
					{...props}
					variant="outline"
					size="icon"
					class="size-7 bg-card/90 backdrop-blur"
					onclick={fit}
				>
					<Maximize class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
		<Hint text="Re-run layout">
			{#snippet child(props)}
				<Button
					{...props}
					variant="outline"
					size="icon"
					class="size-7 bg-card/90 backdrop-blur"
					onclick={relayout}
				>
					<Shuffle class="size-3.5" />
				</Button>
			{/snippet}
		</Hint>
	</div>
</div>
