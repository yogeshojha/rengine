<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import * as Chart from '$lib/components/ui/chart/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { scaleUtc } from 'd3-scale';
	import { Area, AreaChart, ChartClipPath } from 'layerchart';
	import { curveNatural } from 'd3-shape';
	import ChartContainer from '$lib/components/ui/chart/chart-container.svelte';
	import { cubicInOut } from 'svelte/easing';

	interface Props {
		target: Target;
	}

	let { target }: Props = $props();

	let timeRange = $state('3m');

	interface SeriesConfig {
		key: string;
		label: string;
		color: string;
	}

	function getSeriesForTarget(type: TargetType): SeriesConfig[] {
		switch (type) {
			case TargetType.DOMAIN:
				return [
					{ key: 'subdomains', label: 'Subdomains', color: 'var(--chart-1)' },
					{ key: 'ips', label: 'IPs', color: 'var(--chart-2)' },
					{ key: 'ports', label: 'Open Ports', color: 'var(--chart-3)' }
				];
			case TargetType.IP:
				return [
					{ key: 'ports', label: 'Open Ports', color: 'var(--chart-1)' },
					{ key: 'services', label: 'Services', color: 'var(--chart-2)' },
					{ key: 'reverse_dns', label: 'Reverse DNS', color: 'var(--chart-3)' }
				];
			case TargetType.IP_RANGE:
				return [
					{ key: 'live_hosts', label: 'Live Hosts', color: 'var(--chart-1)' },
					{ key: 'ports', label: 'Open Ports', color: 'var(--chart-2)' },
					{ key: 'services', label: 'Services', color: 'var(--chart-3)' }
				];
			case TargetType.ASN:
				return [
					{ key: 'prefixes', label: 'Prefixes', color: 'var(--chart-1)' },
					{ key: 'live_hosts', label: 'Live Hosts', color: 'var(--chart-2)' },
					{ key: 'services', label: 'Services', color: 'var(--chart-3)' }
				];
			case TargetType.URL:
				return [
					{ key: 'technologies', label: 'Technologies', color: 'var(--chart-1)' },
					{ key: 'parameters', label: 'Parameters', color: 'var(--chart-2)' },
					{ key: 'vulnerabilities', label: 'Vulnerabilities', color: 'var(--chart-4)' }
				];
			default:
				return [
					{ key: 'subdomains', label: 'Subdomains', color: 'var(--chart-1)' },
					{ key: 'ips', label: 'IPs', color: 'var(--chart-2)' },
					{ key: 'ports', label: 'Open Ports', color: 'var(--chart-3)' }
				];
		}
	}

	function generateDummyData(type: TargetType): Array<Record<string, number | Date>> {
		const now = new Date();
		const points: Array<Record<string, number | Date>> = [];
		const totalDays = 365;

		// TODO: dummy vals later with props
		const profiles: Record<
			string,
			{ base: Record<string, number>; growth: Record<string, number> }
		> = {
			[TargetType.DOMAIN]: {
				base: { subdomains: 80, ips: 12, ports: 45 },
				growth: { subdomains: 0.5, ips: 0.08, ports: 0.3 }
			},
			[TargetType.IP]: {
				base: { ports: 5, services: 3, reverse_dns: 1 },
				growth: { ports: 0.02, services: 0.015, reverse_dns: 0.005 }
			},
			[TargetType.IP_RANGE]: {
				base: { live_hosts: 60, ports: 350, services: 25 },
				growth: { live_hosts: 0.25, ports: 1.4, services: 0.12 }
			},
			[TargetType.ASN]: {
				base: { prefixes: 14, live_hosts: 800, services: 120 },
				growth: { prefixes: 0.03, live_hosts: 3.0, services: 0.55 }
			},
			[TargetType.URL]: {
				base: { technologies: 6, parameters: 8, vulnerabilities: 2 },
				growth: { technologies: 0.02, parameters: 0.04, vulnerabilities: 0.015 }
			}
		};

		const profile = profiles[type] || profiles[TargetType.DOMAIN];

		for (let i = 0; i < totalDays; i++) {
			const date = new Date(now);
			date.setDate(date.getDate() - (totalDays - i));

			const point: Record<string, number | Date> = { date };

			for (const [key, base] of Object.entries(profile.base)) {
				const growthRate = profile.growth[key];
				const noise = (Math.random() - 0.5) * base * 0.08;
				point[key] = Math.max(0, Math.round(base + growthRate * i + noise));
			}

			points.push(point);
		}

		return points;
	}

	const series = $derived(getSeriesForTarget(target.target_type));

	const chartConfig = $derived(
		Object.fromEntries(
			series.map((s) => [s.key, { label: s.label, color: s.color }])
		) satisfies Chart.ChartConfig
	);

	const allData = $derived(generateDummyData(target.target_type));

	const filteredData = $derived(
		allData.filter((item) => {
			const now = new Date();
			const cutoff = new Date(now);
			switch (timeRange) {
				case '1w':
					cutoff.setDate(cutoff.getDate() - 7);
					break;
				case '1m':
					cutoff.setMonth(cutoff.getMonth() - 1);
					break;
				case '3m':
					cutoff.setMonth(cutoff.getMonth() - 3);
					break;
				case '6m':
					cutoff.setMonth(cutoff.getMonth() - 6);
					break;
				case '1y':
					cutoff.setFullYear(cutoff.getFullYear() - 1);
					break;
			}
			return (item.date as Date) >= cutoff;
		})
	);

	const tickCount = $derived.by(() => {
		switch (timeRange) {
			case '1w':
				return 7;
			case '1m':
				return 6;
			case '3m':
				return 6;
			case '6m':
				return 6;
			case '1y':
				return 12;
			default:
				return 6;
		}
	});

	const gradientIds = $derived(Object.fromEntries(series.map((s) => [s.key, `fill-${s.key}`])));
</script>

<Card.Root class="h-full">
	<Card.Header class="flex items-center gap-2 space-y-0 border-b py-1 sm:flex-row">
		<div class="grid flex-1 gap-0.5 text-center sm:text-start">
			<Card.Title class="text-sm">Attack Surface Over Time</Card.Title>
			<Card.Description class="text-xs">Asset discovery trend across scans</Card.Description>
		</div>
		<Tabs.Root bind:value={timeRange}>
			<Tabs.List class="h-8">
				<Tabs.Trigger value="1w" class="text-xs px-2.5 h-7">1W</Tabs.Trigger>
				<Tabs.Trigger value="1m" class="text-xs px-2.5 h-7">1M</Tabs.Trigger>
				<Tabs.Trigger value="3m" class="text-xs px-2.5 h-7">3M</Tabs.Trigger>
				<Tabs.Trigger value="6m" class="text-xs px-2.5 h-7">6M</Tabs.Trigger>
				<Tabs.Trigger value="1y" class="text-xs px-2.5 h-7">1Y</Tabs.Trigger>
			</Tabs.List>
		</Tabs.Root>
	</Card.Header>
	<Card.Content class="pt-2">
		<ChartContainer config={chartConfig} class="-ml-3 aspect-auto h-[220px] w-full">
			<AreaChart
				legend
				data={filteredData}
				x="date"
				xScale={scaleUtc()}
				{series}
				seriesLayout="stack"
				props={{
					area: {
						curve: curveNatural,
						'fill-opacity': 0.4,
						line: { class: 'stroke-1' },
						motion: 'tween'
					},
					xAxis: {
						ticks: tickCount,
						format: (v: Date) => {
							if (timeRange === '1w') {
								return v.toLocaleDateString('en-US', { weekday: 'short' });
							}
							return v.toLocaleDateString('en-US', {
								month: 'short',
								day: 'numeric'
							});
						}
					},
					yAxis: { format: () => '' }
				}}
			>
				{#snippet marks({ series: chartSeries, getAreaProps })}
					<defs>
						{#each series as s}
							<linearGradient id={gradientIds[s.key]} x1="0" y1="0" x2="0" y2="1">
								<stop offset="5%" stop-color={`var(--color-${s.key})`} stop-opacity={0.8} />
								<stop offset="95%" stop-color={`var(--color-${s.key})`} stop-opacity={0.05} />
							</linearGradient>
						{/each}
					</defs>
					<ChartClipPath
						initialWidth={0}
						motion={{
							width: { type: 'tween', duration: 1000, easing: cubicInOut }
						}}
					>
						{#each chartSeries as s, i (s.key)}
							<Area {...getAreaProps(s, i)} fill={`url(#${gradientIds[s.key]})`} />
						{/each}
					</ChartClipPath>
				{/snippet}
				{#snippet tooltip()}
					<Chart.Tooltip
						labelFormatter={(v: Date) => {
							return v.toLocaleDateString('en-US', {
								month: 'long',
								day: 'numeric',
								year: 'numeric'
							});
						}}
						indicator="line"
					/>
				{/snippet}
			</AreaChart>
		</ChartContainer>
	</Card.Content>
</Card.Root>
