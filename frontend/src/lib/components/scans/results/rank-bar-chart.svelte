<script lang="ts">
	import { BarChart } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';

	interface Props {
		data: { name: string; count: number }[];
		color?: string;
		label?: string;
	}

	let { data, color = 'var(--chart-1)', label = 'Assets' }: Props = $props();

	let config = $derived({ count: { label, color } } satisfies Chart.ChartConfig);
	let height = $derived(Math.max(120, data.length * 34 + 8));
</script>

<div style="height:{height}px">
	<Chart.Container {config} class="aspect-auto h-full w-full">
		<BarChart
			{data}
			orientation="horizontal"
			x="count"
			y="name"
			series={[{ key: 'count', color }]}
			bandPadding={0.28}
			grid={false}
			props={{
				bars: { radius: 5, rounded: 'right' },
				xAxis: { format: () => '', tickLength: 0 },
				yAxis: { tickLength: 0, format: (v: string) => v }
			}}
		>
			{#snippet tooltip()}
				<Chart.Tooltip hideLabel nameKey="count" />
			{/snippet}
		</BarChart>
	</Chart.Container>
</div>
