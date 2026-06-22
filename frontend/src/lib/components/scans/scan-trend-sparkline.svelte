<script lang="ts">
	import { scalePoint } from 'd3-scale';
	import { curveMonotoneX } from 'd3-shape';
	import { AreaChart } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';

	let { values }: { values: number[] } = $props();

	let data = $derived(values.map((v, i) => ({ i: String(i), v })));

	const config = {
		v: { label: 'Subdomains', color: 'var(--chart-1)' }
	} satisfies Chart.ChartConfig;
	const series = [{ key: 'v', label: 'Subdomains', color: 'var(--chart-1)' }];
</script>

{#if data.length > 1}
	<Chart.Container {config} class="h-7 w-24">
		<AreaChart
			{data}
			x="i"
			{series}
			axis={false}
			grid={false}
			legend={false}
			xScale={scalePoint()}
			props={{ area: { curve: curveMonotoneX } }}
		/>
	</Chart.Container>
{/if}
