<script lang="ts">
	import { PieChart } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';

	interface Props {
		data: { key: string; label: string; count: number; color: string }[];
		total: number;
		centerLabel?: string;
	}

	let { data, total, centerLabel = '' }: Props = $props();

	let config = $derived(
		Object.fromEntries(
			data.map((d) => [d.key, { label: d.label, color: d.color }])
		) satisfies Chart.ChartConfig
	);

	let pieData = $derived(
		data.map((d) => ({
			key: d.key,
			label: d.label,
			count: d.count,
			color: `var(--color-${d.key})`
		}))
	);
</script>

<div class="flex items-center gap-4">
	<div class="relative aspect-square w-[124px] shrink-0">
		<Chart.Container {config} class="h-full w-full">
			<PieChart
				data={pieData}
				key="key"
				value="count"
				c="color"
				innerRadius={44}
				padAngle={0.02}
				cornerRadius={3}
				props={{ pie: { motion: 'tween' } }}
			>
				{#snippet tooltip()}
					<Chart.Tooltip hideLabel nameKey="label" />
				{/snippet}
			</PieChart>
		</Chart.Container>
		<div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
			<span class="text-xl font-semibold leading-none tabular-nums">{total}</span>
			{#if centerLabel}<span class="mt-1 text-[10px] text-muted-foreground">{centerLabel}</span
				>{/if}
		</div>
	</div>
	<div class="flex-1 space-y-1.5">
		{#each data as d (d.key)}
			{@const pct = total > 0 ? Math.round((d.count / total) * 100) : 0}
			<div class="flex items-center gap-2 text-xs">
				<span class="h-2.5 w-2.5 shrink-0 rounded-[2px]" style="background:{d.color}"></span>
				<span class="flex-1 truncate">{d.label}</span>
				<span class="font-semibold tabular-nums">{d.count}</span>
				<span class="w-8 shrink-0 text-right text-[11px] tabular-nums text-muted-foreground"
					>{pct}%</span
				>
			</div>
		{/each}
	</div>
</div>
