<script lang="ts">
	import { scalePoint } from 'd3-scale';
	import { curveMonotoneX } from 'd3-shape';
	import { Area, AreaChart, LinearGradient } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';
	import { cn } from '$lib/utils.js';

	let {
		values,
		label = 'Subdomains',
		class: className
	}: { values: number[]; label?: string; class?: string } = $props();

	let data = $derived(values.map((v, i) => ({ i: String(i), v })));

	let config = $derived({ v: { label, color: 'var(--chart-1)' } } satisfies Chart.ChartConfig);
	let series = $derived([{ key: 'v', label, color: 'var(--chart-1)' }]);
	const stops = [
		'color-mix(in oklab, var(--chart-1) 30%, transparent)',
		'color-mix(in oklab, var(--chart-1) 2%, transparent)'
	];
</script>

{#if data.length > 1}
	<Chart.Container {config} class={cn('h-7 w-24', className)}>
		<AreaChart
			{data}
			x="i"
			{series}
			axis={false}
			grid={false}
			legend={false}
			xScale={scalePoint()}
			yDomain={[0, null]}
			yPadding={[0, 6]}
			padding={{ top: 2, right: 1, bottom: 0, left: 1 }}
			props={{ area: { curve: curveMonotoneX, fillOpacity: 1, line: { class: 'stroke-2' } } }}
		>
			{#snippet marks({ visibleSeries, getAreaProps })}
				{#each visibleSeries as s, i (s.key)}
					<LinearGradient {stops} vertical>
						{#snippet children({ gradient })}
							<Area {...getAreaProps(s, i)} fill={gradient} />
						{/snippet}
					</LinearGradient>
				{/each}
			{/snippet}
		</AreaChart>
	</Chart.Container>
{/if}
