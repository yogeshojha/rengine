<script lang="ts">
	import { PieChart } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart/index.js';
	import { TargetType, formatTargetType } from '$lib/types/target';

	interface Props {
		breakdown: { type: TargetType; count: number }[];
		total: number;
		onSelect: (type: TargetType) => void;
	}

	let { breakdown, total, onSelect }: Props = $props();

	const COLOR: Record<TargetType, string> = {
		[TargetType.DOMAIN]: 'var(--chart-1)',
		[TargetType.IP]: 'var(--chart-2)',
		[TargetType.IP_RANGE]: 'var(--chart-3)',
		[TargetType.ASN]: 'var(--chart-4)',
		[TargetType.URL]: 'var(--chart-5)'
	};

	const config: Chart.ChartConfig = {
		[TargetType.DOMAIN]: {
			label: formatTargetType(TargetType.DOMAIN),
			color: COLOR[TargetType.DOMAIN]
		},
		[TargetType.IP]: { label: formatTargetType(TargetType.IP), color: COLOR[TargetType.IP] },
		[TargetType.IP_RANGE]: {
			label: formatTargetType(TargetType.IP_RANGE),
			color: COLOR[TargetType.IP_RANGE]
		},
		[TargetType.ASN]: { label: formatTargetType(TargetType.ASN), color: COLOR[TargetType.ASN] },
		[TargetType.URL]: { label: formatTargetType(TargetType.URL), color: COLOR[TargetType.URL] }
	};

	let rows = $derived(breakdown.filter((b) => b.count > 0));
	let data = $derived(
		rows.map((b) => ({
			type: b.type,
			label: formatTargetType(b.type),
			count: b.count,
			color: `var(--color-${b.type})`
		}))
	);
</script>

<div class="flex flex-col items-center gap-5 sm:flex-row sm:gap-6">
	<div class="relative aspect-square w-[170px] shrink-0">
		<Chart.Container {config} class="h-full w-full">
			<PieChart
				{data}
				key="type"
				value="count"
				c="color"
				innerRadius={58}
				padAngle={0.02}
				cornerRadius={3}
				props={{ pie: { motion: 'tween' } }}
			>
				{#snippet tooltip()}
					<Chart.Tooltip hideLabel nameKey="type" />
				{/snippet}
			</PieChart>
		</Chart.Container>
		<div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
			<span class="text-2xl font-semibold leading-none tabular-nums">{total}</span>
			<span class="mt-1 text-[11px] text-muted-foreground">assets</span>
		</div>
	</div>

	<div class="w-full space-y-0.5">
		{#each rows as row (row.type)}
			{@const pct = total > 0 ? Math.round((row.count / total) * 100) : 0}
			<button
				type="button"
				onclick={() => onSelect(row.type)}
				class="group flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted/40"
			>
				<span class="h-2.5 w-2.5 shrink-0 rounded-[2px]" style="background:{COLOR[row.type]}"
				></span>
				<span class="flex-1 truncate text-sm">{formatTargetType(row.type)}</span>
				<span class="text-sm font-semibold tabular-nums">{row.count}</span>
				<span class="w-9 shrink-0 text-right text-[11px] tabular-nums text-muted-foreground"
					>{pct}%</span
				>
			</button>
		{/each}
	</div>
</div>
