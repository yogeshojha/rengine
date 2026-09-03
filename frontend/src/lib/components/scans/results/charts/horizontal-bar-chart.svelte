<script lang="ts">
	import { BarChart } from 'layerchart';
	import { scaleBand } from 'd3-scale';
	import { cubicInOut } from 'svelte/easing';
	import * as Chart from '$lib/components/ui/chart';

	export interface Bar {
		label: string;
		count: number;
	}

	interface Props {
		bars: Bar[];
		valueLabel: string;
		labelWidth?: number;
		onSelect?: (label: string) => void;
	}

	let { bars, valueLabel, labelWidth = 96, onSelect }: Props = $props();

	const ROW_HEIGHT = 32;

	let config = $derived({
		count: { label: valueLabel, color: 'var(--chart-1)' }
	} satisfies Chart.ChartConfig);
	let height = $derived(bars.length * ROW_HEIGHT + 8);
</script>

<Chart.Container {config} class="aspect-auto w-full" style="height:{height}px">
	<BarChart
		data={bars}
		orientation="horizontal"
		yScale={scaleBand().padding(0.35)}
		y="label"
		x="count"
		series={[{ key: 'count', label: valueLabel, color: config.count.color }]}
		padding={{ left: labelWidth, right: 44, top: 4, bottom: 4 }}
		grid={false}
		rule={false}
		axis="y"
		labels={{ offset: 8, format: (v: unknown) => Math.round(Number(v)).toLocaleString() }}
		props={{
			bars: {
				stroke: 'none',
				radius: 4,
				rounded: 'right',
				initialWidth: 0,
				initialX: 0,
				motion: {
					x: { type: 'tween', duration: 500, easing: cubicInOut },
					width: { type: 'tween', duration: 500, easing: cubicInOut }
				},
				class: onSelect ? 'cursor-pointer' : ''
			},
			highlight: { area: { fill: 'none' } },
			yAxis: { tickLength: 0, tickLabelProps: { svgProps: { x: -12 } } }
		}}
		onBarClick={(_e, detail) => onSelect?.((detail.data as Bar).label)}
	>
		{#snippet tooltip()}
			<Chart.Tooltip />
		{/snippet}
	</BarChart>
</Chart.Container>
