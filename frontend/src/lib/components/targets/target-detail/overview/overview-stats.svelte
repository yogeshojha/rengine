<script lang="ts">
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import StatCard from './stat-card.svelte';
	import {
		Globe,
		Server,
		Network,
		ShieldAlert,
		Layers,
		Waypoints,
		Cpu,
		Link,
		Timer,
		Variable,
		MonitorCheck
	} from 'lucide-svelte';
	import type { Component } from 'svelte';

	interface StatCardConfig {
		label: string;
		value: number;
		unit?: string;
		icon: any;
		delta: number | null;
		deltaContext: 'neutral' | 'inverse';
		previousValue: number | null;
		accent?: 'default' | 'danger' | 'success';
	}

	interface Props {
		target: Target;
	}

	let { target }: Props = $props();

	// dummy data until api is build
	function getDomainStats(): StatCardConfig[] {
		return [
			{
				label: 'Subdomains',
				value: 247,
				icon: Globe,
				delta: 12,
				deltaContext: 'neutral',
				previousValue: 235
			},
			{
				label: 'IPs Resolved',
				value: 38,
				icon: Server,
				delta: 3,
				deltaContext: 'neutral',
				previousValue: 35
			},
			{
				label: 'Open Ports',
				value: 156,
				icon: Network,
				delta: -4,
				deltaContext: 'neutral',
				previousValue: 160
			},
			{
				label: 'Vulnerabilities',
				value: 84,
				icon: ShieldAlert,
				delta: 3,
				deltaContext: 'inverse',
				previousValue: 81,
				accent: 'danger'
			}
		];
	}

	function getIpStats(): StatCardConfig[] {
		return [
			{
				label: 'Open Ports',
				value: 12,
				icon: Network,
				delta: 2,
				deltaContext: 'neutral',
				previousValue: 10
			},
			{
				label: 'Services',
				value: 8,
				icon: Cpu,
				delta: 1,
				deltaContext: 'neutral',
				previousValue: 7
			},
			{
				label: 'Reverse DNS',
				value: 3,
				icon: Link,
				delta: null,
				deltaContext: 'neutral',
				previousValue: 3
			},
			{
				label: 'Vulnerabilities',
				value: 17,
				icon: ShieldAlert,
				delta: -2,
				deltaContext: 'inverse',
				previousValue: 19,
				accent: 'success'
			}
		];
	}

	function getIpRangeStats(): StatCardConfig[] {
		return [
			{
				label: 'Live Hosts',
				value: 142,
				icon: MonitorCheck,
				delta: 8,
				deltaContext: 'neutral',
				previousValue: 134
			},
			{
				label: 'Open Ports',
				value: 847,
				icon: Network,
				delta: 23,
				deltaContext: 'neutral',
				previousValue: 824
			},
			{
				label: 'Services',
				value: 64,
				icon: Cpu,
				delta: 5,
				deltaContext: 'neutral',
				previousValue: 59
			},
			{
				label: 'Vulnerabilities',
				value: 213,
				icon: ShieldAlert,
				delta: 14,
				deltaContext: 'inverse',
				previousValue: 199,
				accent: 'danger'
			}
		];
	}

	function getAsnStats(): StatCardConfig[] {
		return [
			{
				label: 'Prefixes',
				value: target.bgp?.prefix_count ?? 24,
				icon: Layers,
				delta: 2,
				deltaContext: 'neutral',
				previousValue: 22
			},
			{
				label: 'Live Hosts',
				value: 1847,
				icon: MonitorCheck,
				delta: 43,
				deltaContext: 'neutral',
				previousValue: 1804
			},
			{
				label: 'Services',
				value: 312,
				icon: Cpu,
				delta: 18,
				deltaContext: 'neutral',
				previousValue: 294
			},
			{
				label: 'Vulnerabilities',
				value: 567,
				icon: ShieldAlert,
				delta: -12,
				deltaContext: 'inverse',
				previousValue: 579,
				accent: 'success'
			}
		];
	}

	function getUrlStats(): StatCardConfig[] {
		return [
			{
				label: 'Technologies',
				value: 14,
				icon: Waypoints,
				delta: 2,
				deltaContext: 'neutral',
				previousValue: 12
			},
			{
				label: 'Parameters',
				value: 23,
				icon: Variable,
				delta: 5,
				deltaContext: 'neutral',
				previousValue: 18
			},
			{
				label: 'Vulnerabilities',
				value: 7,
				icon: ShieldAlert,
				delta: 1,
				deltaContext: 'inverse',
				previousValue: 6,
				accent: 'danger'
			},
			{
				label: 'Avg Response',
				value: 284,
				unit: 'ms',
				icon: Timer,
				delta: -42,
				deltaContext: 'inverse',
				previousValue: 326
			}
		];
	}

	const stats = $derived.by((): StatCardConfig[] => {
		switch (target.target_type) {
			case TargetType.DOMAIN:
				return getDomainStats();
			case TargetType.IP:
				return getIpStats();
			case TargetType.IP_RANGE:
				return getIpRangeStats();
			case TargetType.ASN:
				return getAsnStats();
			case TargetType.URL:
				return getUrlStats();
			default:
				return getDomainStats();
		}
	});
</script>

<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
	{#each stats as stat}
		<StatCard
			label={stat.label}
			value={stat.value}
			unit={stat.unit}
			icon={stat.icon}
			delta={stat.delta}
			deltaContext={stat.deltaContext}
			previousValue={stat.previousValue}
			accent={stat.accent}
		/>
	{/each}
</div>
