<script lang="ts">
	import { geoOrthographic, geoPath, geoGraticule10, geoDistance } from 'd3-geo';
	import { feature } from 'topojson-client';
	import type { GeoPermissibleObjects } from 'd3-geo';
	import topology from '$lib/data/land-110m.json';
	import { countryGeo } from '$lib/config/country-geo';

	interface Entry {
		code: string;
		count: number;
	}

	interface Props {
		entries: Entry[];
		size?: number;
		spin?: boolean;
		activeCode?: string | null;
		onPick?: (code: string) => void;
		onHover?: (code: string | null) => void;
	}

	let { entries, size = 240, spin = true, activeCode = null, onPick, onHover }: Props = $props();

	// drift around the dominant country rather than spinning past it — the globe
	// has to still be showing what the headline is talking about
	const SWING_DEGREES = 18;
	const SWING_SECONDS = 26;
	const MIN_R = 3.5;
	const MAX_R = 10;

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const land = feature(topology as any, (topology as any).objects.land) as GeoPermissibleObjects;

	let plotted = $derived(
		entries
			.map((e) => ({ ...e, geo: countryGeo(e.code) }))
			.filter((e): e is Entry & { geo: NonNullable<ReturnType<typeof countryGeo>> } => !!e.geo)
	);
	let peak = $derived(Math.max(1, ...plotted.map((p) => p.count)));
	// open on the dominant country, then drift
	let startLon = $derived(plotted[0]?.geo.lonLat[0] ?? 0);
	let tilt = $derived(
		plotted.length ? plotted.reduce((n, p) => n + p.geo.lonLat[1], 0) / plotted.length / 2 : 15
	);

	let swing = $state(0);
	let paused = $state(false);

	$effect(() => {
		if (!spin || paused) return;
		if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
		let frame = 0;
		const started = performance.now();
		const step = (now: number) => {
			const phase = ((now - started) / 1000 / SWING_SECONDS) * Math.PI * 2;
			swing = Math.sin(phase) * SWING_DEGREES;
			frame = requestAnimationFrame(step);
		};
		frame = requestAnimationFrame(step);
		return () => cancelAnimationFrame(frame);
	});

	let rotate = $derived<[number, number]>([-startLon + swing, -tilt]);
	let projection = $derived(
		geoOrthographic()
			.rotate(rotate)
			.fitExtent(
				[
					[2, 2],
					[size - 2, size - 2]
				],
				{ type: 'Sphere' }
			)
	);
	let draw = $derived(geoPath(projection));
	let sphere = $derived(draw({ type: 'Sphere' }) ?? '');
	let grid = $derived(draw(geoGraticule10()) ?? '');
	let landPath = $derived(draw(land) ?? '');
	let center = $derived<[number, number]>([-rotate[0], -rotate[1]]);

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
</script>

<svg
	viewBox="0 0 {size} {size}"
	width={size}
	height={size}
	role="img"
	aria-label="Addresses by country"
	class="overflow-visible"
	onpointerenter={() => (paused = true)}
	onpointerleave={() => {
		paused = false;
		onHover?.(null);
	}}
>
	<defs>
		<radialGradient id="globe-shade" cx="35%" cy="30%" r="75%">
			<stop offset="0%" stop-color="var(--primary)" stop-opacity="0.16" />
			<stop offset="100%" stop-color="var(--primary)" stop-opacity="0.03" />
		</radialGradient>
	</defs>

	<path d={sphere} fill="url(#globe-shade)" stroke="var(--border)" stroke-width="1" />
	<path d={landPath} fill="var(--muted-foreground)" opacity="0.55" />
	<path d={grid} fill="none" stroke="var(--border)" stroke-width="0.4" opacity="0.5" />
	<path d={sphere} fill="none" stroke="var(--border)" stroke-width="1" />

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
			<circle
				cx={dot.x}
				cy={dot.y}
				r={dot.r + 4}
				fill="var(--primary)"
				opacity={active ? 0.28 : 0.12}
			/>
			<circle
				cx={dot.x}
				cy={dot.y}
				r={dot.r}
				fill="var(--primary)"
				stroke="var(--background)"
				stroke-width="1"
			/>
		</g>
	{/each}
</svg>
