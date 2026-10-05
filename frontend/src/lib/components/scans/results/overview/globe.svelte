<script lang="ts">
	import { geoOrthographic, geoPath, geoGraticule10, geoDistance } from 'd3-geo';
	import type { GeoPermissibleObjects } from 'd3-geo';
	import { feature } from 'topojson-client';
	import topology from '$lib/data/land-110m.json';
	import { countryGeo } from '$lib/config/country-geo';
	import { cn } from '$lib/utils';

	interface GlobeEntry {
		code: string;
		count: number;
	}

	interface Props {
		entries: GlobeEntry[];
		size?: number;
		class?: string;
		activeCode?: string | null;
		onPick?: (code: string) => void;
		onHover?: (code: string | null) => void;
	}

	let {
		entries,
		size = 240,
		class: className,
		activeCode = null,
		onPick,
		onHover
	}: Props = $props();

	const uid = $props.id();
	const SPIN_SECONDS = 20;
	const MAX_FRAME_MS = 100;
	const MIN_R = 2.25;
	const MAX_R = 5.5;
	const HIT_R = 9;
	const INSET = 10;
	const DEFAULT_VIEW: [number, number] = [-20, 25];
	const RING_STEP = 3;
	const RINGS = [
		{ inc: 24, precess: 96 },
		{ inc: 58, precess: -132 },
		{ inc: -38, precess: 168 }
	];

	const ringLine = (inc: number, node: number): GeoPermissibleObjects => {
		const i = (inc * Math.PI) / 180;
		const coordinates: [number, number][] = [];
		for (let t = 0; t <= 360; t += RING_STEP) {
			const a = (t * Math.PI) / 180;
			coordinates.push([
				node + (Math.atan2(Math.cos(i) * Math.sin(a), Math.cos(a)) * 180) / Math.PI,
				(Math.asin(Math.sin(i) * Math.sin(a)) * 180) / Math.PI
			]);
		}
		return { type: 'LineString', coordinates };
	};

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const land = feature(topology as any, (topology as any).objects.land) as GeoPermissibleObjects;

	let plotted = $derived(
		entries
			.map((e) => ({ ...e, geo: countryGeo(e.code) }))
			.filter((e): e is GlobeEntry & { geo: NonNullable<ReturnType<typeof countryGeo>> } => !!e.geo)
	);
	let peak = $derived(Math.max(1, ...plotted.map((p) => p.count)));
	let lead = $derived(
		plotted.reduce<(typeof plotted)[number] | undefined>(
			(top, p) => (!top || p.count > top.count ? p : top),
			undefined
		)
	);
	let anchor = $derived<[number, number]>(lead?.geo.lonLat ?? DEFAULT_VIEW);
	let tilt = $derived(
		plotted.length
			? plotted.reduce((n, p) => n + p.geo.lonLat[1], 0) / plotted.length / 2
			: DEFAULT_VIEW[1]
	);

	let clock = $state(0);
	let seconds = 0;
	let held = false;

	$effect(() => {
		if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
		let frame = 0;
		let last = performance.now();
		const step = (now: number) => {
			if (!held) {
				seconds += Math.min(now - last, MAX_FRAME_MS) / 1000;
				clock = seconds;
			}
			last = now;
			frame = requestAnimationFrame(step);
		};
		frame = requestAnimationFrame(step);
		return () => cancelAnimationFrame(frame);
	});

	let spin = $derived(((clock / SPIN_SECONDS) * 360) % 360);

	let rotate = $derived<[number, number]>([-anchor[0] + spin, -tilt]);
	let projection = $derived(
		geoOrthographic()
			.rotate(rotate)
			.fitExtent(
				[
					[INSET, INSET],
					[size - INSET, size - INSET]
				],
				{ type: 'Sphere' }
			)
	);
	let draw = $derived(geoPath(projection));
	let sphere = $derived(draw({ type: 'Sphere' }) ?? '');
	let grid = $derived(draw(geoGraticule10()) ?? '');
	let landPath = $derived(draw(land) ?? '');
	let radius = $derived(projection.scale());
	let center = $derived<[number, number]>([-rotate[0], -rotate[1]]);
	let mid = $derived(size / 2);

	let dots = $derived(
		plotted
			.map((p) => {
				const xy = projection(p.geo.lonLat);
				const front = geoDistance(p.geo.lonLat, center) < Math.PI / 2;
				return xy && front
					? {
							code: p.code,
							name: p.geo.name,
							count: p.count,
							x: xy[0],
							y: xy[1],
							r: MIN_R + Math.sqrt(p.count / peak) * (MAX_R - MIN_R)
						}
					: null;
			})
			.filter((d): d is NonNullable<typeof d> => d !== null)
			.sort((a, b) => b.r - a.r)
	);

	let rings = $derived(
		RINGS.map((r, i) => ({
			i,
			d: draw(ringLine(r.inc, -spin + (((clock / r.precess) * 360) % 360))) ?? ''
		})).filter((r) => r.d)
	);
</script>

<svg
	viewBox="0 0 {size} {size}"
	role="img"
	aria-label="Addresses by country"
	class={cn('overflow-visible', className)}
	onpointerenter={() => (held = true)}
	onpointerleave={() => {
		held = false;
		onHover?.(null);
	}}
>
	<defs>
		<radialGradient id="{uid}-sea" cx="36%" cy="30%" r="74%">
			<stop offset="0%" stop-color="var(--series)" stop-opacity="0.2" />
			<stop offset="100%" stop-color="var(--series)" stop-opacity="0.04" />
		</radialGradient>
	</defs>

	<circle
		cx={mid}
		cy={mid}
		r={radius + 6}
		fill="none"
		stroke="var(--series)"
		stroke-width="4"
		opacity="0.05"
	/>
	<circle
		cx={mid}
		cy={mid}
		r={radius + 2.5}
		fill="none"
		stroke="var(--series)"
		stroke-width="3"
		opacity="0.1"
	/>
	<path d={sphere} fill="url(#{uid}-sea)" />
	<path d={grid} fill="none" stroke="var(--border)" stroke-width="0.5" opacity="0.8" />
	<path d={landPath} fill="var(--muted-foreground)" opacity="0.45" />
	<path d={sphere} fill="none" stroke="var(--border)" stroke-width="1" />

	{#each rings as ring (ring.i)}
		<path class="ring" d={ring.d} />
	{/each}

	{#each dots as dot (dot.code)}
		{@const active = activeCode === dot.code}
		<g
			class="cursor-pointer"
			role="button"
			tabindex="0"
			aria-label="{dot.name}, {dot.count} addresses"
			onclick={() => onPick?.(dot.code)}
			onkeydown={(e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					onPick?.(dot.code);
				}
			}}
			onpointerenter={() => onHover?.(dot.code)}
		>
			<circle cx={dot.x} cy={dot.y} r={HIT_R} fill="transparent" />
			<circle
				cx={dot.x}
				cy={dot.y}
				r={dot.r + 3.5}
				fill="none"
				stroke="var(--primary)"
				stroke-width="1"
				opacity={active ? 0.55 : 0.2}
			/>
			<circle
				cx={dot.x}
				cy={dot.y}
				r={dot.r}
				fill="var(--series)"
				stroke="var(--background)"
				stroke-width="0.75"
			/>
		</g>
	{/each}
</svg>

<style>
	.ring {
		fill: none;
		stroke: var(--series);
		stroke-width: 0.75;
		opacity: 0.2;
	}
</style>
