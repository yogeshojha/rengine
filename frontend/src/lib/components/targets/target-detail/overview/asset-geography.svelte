<script lang="ts">
	import { onMount } from 'svelte';
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as HoverCard from '$lib/components/ui/hover-card/index.js';
	import { geoNaturalEarth1, geoPath } from 'd3-geo';
	import type { GeoPermissibleObjects } from 'd3-geo';
	import { feature } from 'topojson-client';
	import type { Topology } from 'topojson-specification';

	interface Props {
		target: Target;
	}

	let { target }: Props = $props();

	let countries = $state<GeoPermissibleObjects[]>([]);
	let outline = $state<GeoPermissibleObjects | null>(null);

	const width = 800;
	const height = 420;

	const projection = geoNaturalEarth1()
		.scale(150)
		.translate([width / 2, height / 2]);

	const pathGenerator = geoPath(projection);

	// ── Load world data ──
	onMount(async () => {
		const world: Topology = await import('world-atlas/countries-110m.json' as string);
		const land = feature(world, world.objects.countries);
		if ('features' in land) {
			countries = land.features;
		}
		outline = { type: 'Sphere' };
	});

	// ── Location data ──

	interface GeoLocation {
		lat: number;
		lng: number;
		city: string;
		country: string;
		assetCount: number;
		asn?: string;
		ip?: string;
	}

	function getLocations(type: TargetType): GeoLocation[] {
		const all: GeoLocation[] = [
			{ lat: 37.77, lng: -122.42, city: 'San Francisco', country: 'US', assetCount: 42, asn: 'AS13335', ip: '104.16.x.x' },
			{ lat: 39.04, lng: -77.49, city: 'Ashburn', country: 'US', assetCount: 78, asn: 'AS14618', ip: '52.x.x.x' },
			{ lat: 51.51, lng: -0.13, city: 'London', country: 'UK', assetCount: 23, asn: 'AS16509', ip: '18.x.x.x' },
			{ lat: 50.11, lng: 8.68, city: 'Frankfurt', country: 'DE', assetCount: 18, asn: 'AS16509', ip: '3.x.x.x' },
			{ lat: 1.35, lng: 103.82, city: 'Singapore', country: 'SG', assetCount: 12, asn: 'AS16509', ip: '13.x.x.x' },
			{ lat: 35.68, lng: 139.69, city: 'Tokyo', country: 'JP', assetCount: 8, asn: 'AS16509', ip: '35.x.x.x' },
			{ lat: -33.87, lng: 151.21, city: 'Sydney', country: 'AU', assetCount: 5, asn: 'AS16509', ip: '54.x.x.x' },
			{ lat: 19.08, lng: 72.88, city: 'Mumbai', country: 'IN', assetCount: 14, asn: 'AS16509', ip: '15.x.x.x' }
		];

		if (type === TargetType.IP) return all.slice(0, 3);
		if (type === TargetType.URL) return all.slice(0, 2);
		return all;
	}

	const locations = $derived(getLocations(target.target_type));
	const totalAssets = $derived(locations.reduce((sum, l) => sum + l.assetCount, 0));
	const regionCount = $derived(new Set(locations.map((l) => l.country)).size);

	const projectedLocations = $derived(
		locations.map((loc) => {
			const coords = projection([loc.lng, loc.lat]);
			return {
				...loc,
				x: coords?.[0] ?? 0,
				y: coords?.[1] ?? 0,
				r: Math.max(4, Math.min(10, Math.sqrt(loc.assetCount) * 1.5))
			};
		})
	);
</script>

<Card.Root class="overflow-hidden h-full flex flex-col">
	<Card.Header class="flex items-center gap-2 space-y-0 border-b py-3 sm:flex-row">
		<div class="grid flex-1 gap-0.5 text-center sm:text-start">
			<Card.Title class="text-sm">Asset Geography</Card.Title>
			<Card.Description class="text-xs">
				<span class="tabular-nums">{totalAssets}</span> assets across
				<span class="tabular-nums">{regionCount}</span> regions
			</Card.Description>
		</div>
	</Card.Header>
	<Card.Content class="p-0 flex-1 flex flex-col">
		<div class="flex-1 min-h-[200px] overflow-hidden relative">
			<svg viewBox="0 0 {width} {height}" class="w-full h-full" preserveAspectRatio="xMidYMid meet">
				<!-- Globe outline -->
				{#if outline}
					<path
						d={pathGenerator(outline) ?? ''}
						class="fill-none stroke-border/30"
						stroke-width="0.5"
					/>
				{/if}

				<!-- Country shapes -->
				{#each countries as country}
					<path
						d={pathGenerator(country) ?? ''}
						class="geo-land fill-muted stroke-border/20"
						stroke-width="0.3"
					/>
				{/each}

				<!-- Ripple rings + dots -->
				{#each projectedLocations as loc}
					<!-- Ripple 1 -->
					<circle
						cx={loc.x}
						cy={loc.y}
						r={loc.r}
						class="fill-none stroke-sky-400/30"
						stroke-width="1"
					>
						<animate attributeName="r" from={loc.r} to={loc.r * 4} dur="3s" repeatCount="indefinite" />
						<animate attributeName="opacity" from="0.5" to="0" dur="3s" repeatCount="indefinite" />
					</circle>

					<!-- Ripple 2 (staggered) -->
					<circle
						cx={loc.x}
						cy={loc.y}
						r={loc.r}
						class="fill-none stroke-sky-400/20"
						stroke-width="0.8"
					>
						<animate attributeName="r" from={loc.r} to={loc.r * 4} dur="3s" begin="1s" repeatCount="indefinite" />
						<animate attributeName="opacity" from="0.4" to="0" dur="3s" begin="1s" repeatCount="indefinite" />
					</circle>
				{/each}

				<!-- Solid dots (on top of ripples) -->
				{#each projectedLocations as loc}
					<circle
						cx={loc.x}
						cy={loc.y}
						r={loc.r}
						class="geo-dot"
						fill="rgba(56,189,248,0.75)"
						stroke="rgba(56,189,248,0.25)"
						stroke-width="1.5"
					/>
				{/each}
			</svg>

			<!-- HoverCard triggers overlaid on the SVG -->
			{#each projectedLocations as loc}
				<HoverCard.Root>
					<HoverCard.Trigger>
						<div
							class="absolute cursor-default"
							style="
								left: calc({(loc.x / width) * 100}% - {loc.r + 4}px);
								top: calc({(loc.y / height) * 100}% - {loc.r + 4}px);
								width: {(loc.r + 4) * 2}px;
								height: {(loc.r + 4) * 2}px;
							"
						></div>
					</HoverCard.Trigger>
					<HoverCard.Content class="w-56 p-0" side="top" sideOffset={12}>
						<div class="px-3 py-2 border-b">
							<p class="text-xs font-semibold">{loc.city}, {loc.country}</p>
						</div>
						<div class="px-3 py-2 space-y-1.5">
							<div class="flex items-center justify-between text-xs">
								<span class="text-muted-foreground">Assets</span>
								<span class="font-medium tabular-nums">{loc.assetCount}</span>
							</div>
							{#if loc.asn}
								<div class="flex items-center justify-between text-xs">
									<span class="text-muted-foreground">ASN</span>
									<span class="font-mono text-[11px]">{loc.asn}</span>
								</div>
							{/if}
							{#if loc.ip}
								<div class="flex items-center justify-between text-xs">
									<span class="text-muted-foreground">IP Range</span>
									<span class="font-mono text-[11px]">{loc.ip}</span>
								</div>
							{/if}
						</div>
					</HoverCard.Content>
				</HoverCard.Root>
			{/each}
		</div>
	</Card.Content>
</Card.Root>

<style>
	.geo-land {
		transition: fill 0.2s ease;
	}
</style>
