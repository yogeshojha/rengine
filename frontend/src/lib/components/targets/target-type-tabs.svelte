<script lang="ts">
	import { TargetType } from '$lib/types/target';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Globe, MapPin, Hash, Building2, Link2, Layers } from 'lucide-svelte';

	interface Props {
		counts: {
			all: number;
			domain: number;
			ip: number;
			ip_range: number;
			asn: number;
			url: number;
		};
		activeTab: string;
		onTabChange: (value: string) => void;
	}

	let { counts, activeTab, onTabChange }: Props = $props();

	const tabs = [
		{ value: 'all', label: 'All', icon: Layers },
		{ value: TargetType.DOMAIN, label: 'Domains', icon: Globe },
		{ value: TargetType.IP, label: 'IPs', icon: MapPin },
		{ value: TargetType.IP_RANGE, label: 'IP Ranges', icon: Hash },
		{ value: TargetType.ASN, label: 'ASNs', icon: Building2 },
		{ value: TargetType.URL, label: 'URLs', icon: Link2 }
	];

	function getCount(value: string): number {
		return counts[value as keyof typeof counts] ?? 0;
	}
</script>

<Tabs.Root value={activeTab} onValueChange={(v) => v && onTabChange(v)} class="w-full">
	<Tabs.List class="h-auto bg-muted/80 rounded-lg inline-flex gap-1">
		{#each tabs as tab}
			{@const count = getCount(tab.value)}
			<Tabs.Trigger
				value={tab.value}
				class="flex items-center gap-2 px-4 py-1 text-sm rounded-md data-[state=active]:bg-background data-[state=active]:shadow-sm transition-all"
			>
				<tab.icon class="h-4 w-4" />
				<span>{tab.label}</span>
				<span
					class="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-muted data-[state=active]:bg-primary/10 data-[state=active]:text-primary font-medium tabular-nums"
				>
					{count}
				</span>
			</Tabs.Trigger>
		{/each}
	</Tabs.List>
</Tabs.Root>
