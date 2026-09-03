<script lang="ts">
	import { PieChart } from 'layerchart';
	import * as Chart from '$lib/components/ui/chart';

	export interface DonutSlice {
		key: string;
		label: string;
		count: number;
		color: string;
		filter?: string;
	}

	interface Props {
		slices: DonutSlice[];
		total: number;
		centerLabel: string;
		onSelect?: (filter: string) => void;
	}

	let { slices, total, centerLabel, onSelect }: Props = $props();

	let config = $derived(
		Object.fromEntries(
			slices.map((s) => [s.key, { label: s.label, color: s.color }])
		) satisfies Chart.ChartConfig
	);
	let data = $derived(
		slices.map((s) => ({
			key: s.key,
			label: s.label,
			count: s.count,
			color: `var(--color-${s.key})`
		}))
	);
	const pct = (n: number) => (total > 0 ? Math.round((n / total) * 100) : 0);
</script>

<div class="flex items-center gap-3">
	<div class="relative size-[96px] shrink-0">
		<Chart.Container {config} class="aspect-square h-full w-full">
			<PieChart
				{data}
				key="key"
				value="count"
				c="color"
				innerRadius={-10}
				padAngle={0.03}
				cornerRadius={2}
				props={{ pie: { motion: 'tween', sort: null } }}
			>
				{#snippet tooltip()}
					<Chart.Tooltip hideLabel />
				{/snippet}
			</PieChart>
		</Chart.Container>
		<div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
			<span class="text-lg leading-none font-semibold">{total.toLocaleString()}</span>
			<span class="mt-1 text-[10px] text-muted-foreground">{centerLabel}</span>
		</div>
	</div>

	<ul class="flex min-w-0 flex-1 flex-col gap-0.5">
		{#each slices as s (s.key)}
			<li>
				{#if s.filter && onSelect}
					<button
						type="button"
						class="flex w-full cursor-pointer items-center gap-2 rounded-md px-1 py-1 text-left transition-colors hover:bg-muted/40"
						onclick={() => onSelect(s.filter!)}
					>
						{@render row(s)}
					</button>
				{:else}
					<div class="flex w-full items-center gap-2 px-1 py-1">
						{@render row(s)}
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</div>

{#snippet row(s: DonutSlice)}
	<span class="size-2.5 shrink-0 rounded-[2px]" style="background:{s.color}"></span>
	<span class="min-w-0 flex-1 text-xs leading-tight">{s.label}</span>
	<span class="text-xs font-medium tabular-nums">{s.count.toLocaleString()}</span>
	<span class="w-7 shrink-0 text-right text-[11px] text-muted-foreground tabular-nums">
		{pct(s.count)}%
	</span>
{/snippet}
