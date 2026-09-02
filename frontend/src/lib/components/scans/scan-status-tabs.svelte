<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import {
		SCAN_STATUS_TABS,
		scanStatusTabCount,
		type ScanStatusTab
	} from '$lib/utilities/scan-status';
	import type { ScanStatusCounts } from '$lib/types/scan';

	interface Props {
		active: ScanStatusTab;
		counts: ScanStatusCounts | null;
		total: number;
		onChange: (tab: ScanStatusTab) => void;
	}

	let { active, counts, total, onChange }: Props = $props();

	function countClass(tab: ScanStatusTab, n: number): string {
		if (n === 0) return 'text-muted-foreground/50';
		if (tab === 'failed') return 'text-destructive';
		if (tab === 'active') return 'text-info';
		return 'text-muted-foreground';
	}
</script>

<Tabs.Root value={active} onValueChange={(v) => v && onChange(v as ScanStatusTab)}>
	<ScrollArea.Root orientation="horizontal" class="w-full">
		<Tabs.List class="-mb-px h-auto w-full justify-start gap-0 rounded-none bg-transparent p-0">
			{#each SCAN_STATUS_TABS as tab (tab.key)}
				<Tabs.Trigger
					value={tab.key}
					class="flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
				>
					{tab.label}
					{#if counts}
						{@const n = scanStatusTabCount(tab.key, counts, total)}
						<span class="text-xs tabular-nums {countClass(tab.key, n)}">{n}</span>
					{/if}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>
	</ScrollArea.Root>
</Tabs.Root>
