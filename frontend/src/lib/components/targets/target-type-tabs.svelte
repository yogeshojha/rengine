<script lang="ts">
	import { TargetType, formatTargetType } from '$lib/types/target';
	import * as Tabs from '$lib/components/ui/tabs';
	import { Layers } from 'lucide-svelte';
	import { TARGET_TYPE_ICONS_COMPACT } from '$lib/config/icons';

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
		...Object.entries(TARGET_TYPE_ICONS_COMPACT).map(([value, icon]) => ({
			value,
			label: formatTargetType(value as TargetType) + 's',
			icon
		}))
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
