<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs';
	import * as ScrollArea from '$lib/components/ui/scroll-area';

	interface Tab {
		key: string;
		label: string;
	}

	interface Props {
		tabs: Tab[];
		value: string;
		counts?: Record<string, number> | null;
		countClass?: (key: string, n: number) => string;
		onChange: (key: string) => void;
	}

	let { tabs, value, counts = null, countClass, onChange }: Props = $props();

	function tone(key: string, n: number): string {
		if (countClass) return countClass(key, n);
		return n === 0 ? 'text-muted-foreground/50' : 'text-muted-foreground';
	}
</script>

<Tabs.Root {value} onValueChange={(v) => v && onChange(v)}>
	<ScrollArea.Root orientation="horizontal" class="w-full">
		<Tabs.List class="-mb-px h-auto w-full justify-start gap-0 rounded-none bg-transparent p-0">
			{#each tabs as tab (tab.key)}
				<Tabs.Trigger
					value={tab.key}
					class="flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
				>
					{tab.label}
					{#if counts}
						{@const n = counts[tab.key] ?? 0}
						<span class="text-xs tabular-nums {tone(tab.key, n)}">{n.toLocaleString()}</span>
					{/if}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>
	</ScrollArea.Root>
</Tabs.Root>
