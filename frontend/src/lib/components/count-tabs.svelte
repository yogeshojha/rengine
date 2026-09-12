<script lang="ts" module>
	export interface Tab {
		key: string;
		label: string;
		href?: string;
	}
</script>

<script lang="ts">
	import * as Tabs from '$lib/components/ui/tabs';
	import * as ScrollArea from '$lib/components/ui/scroll-area';

	interface Props {
		tabs: Tab[];
		value: string;
		counts?: Record<string, number | null | undefined> | null;
		capped?: Record<string, boolean> | null;
		countClass?: (key: string, n: number) => string;
		onChange?: (key: string) => void;
	}

	let { tabs, value, counts = null, capped = null, countClass, onChange }: Props = $props();

	const TRIGGER =
		'flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent';

	function tone(key: string, n: number): string {
		if (countClass) return countClass(key, n);
		return n === 0 ? 'text-muted-foreground/50' : 'text-muted-foreground';
	}
</script>

{#snippet body(tab: Tab)}
	{tab.label}
	{#if counts}
		{@const n = counts[tab.key]}
		{#if n != null}
			<span class="text-xs tabular-nums {tone(tab.key, n)}">
				{n.toLocaleString()}{capped?.[tab.key] ? '+' : ''}
			</span>
		{/if}
	{/if}
{/snippet}

<Tabs.Root {value} onValueChange={(v) => v && onChange?.(v)}>
	<ScrollArea.Root orientation="horizontal" class="w-full">
		<Tabs.List class="-mb-px h-auto w-full justify-start gap-0 rounded-none bg-transparent p-0">
			{#each tabs as tab (tab.key)}
				{#if tab.href}
					<Tabs.Trigger value={tab.key} class={TRIGGER}>
						{#snippet child({ props }: { props: Record<string, unknown> })}
							<a {...props} href={tab.href}>{@render body(tab)}</a>
						{/snippet}
					</Tabs.Trigger>
				{:else}
					<Tabs.Trigger value={tab.key} class={TRIGGER}>{@render body(tab)}</Tabs.Trigger>
				{/if}
			{/each}
		</Tabs.List>
	</ScrollArea.Root>
</Tabs.Root>
