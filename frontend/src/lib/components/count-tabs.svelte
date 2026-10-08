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
	import { safeHref } from '$lib/utilities/links';

	interface Props {
		tabs: Tab[];
		value: string;
		counts?: Record<string, number | null | undefined> | null;
		capped?: Record<string, boolean> | null;
		countClass?: (key: string, n: number) => string;
		onChange?: (key: string) => void;
	}

	let { tabs, value, counts = null, capped = null, countClass, onChange }: Props = $props();

	function tone(key: string, n: number): string {
		return countClass?.(key, n) ?? 'text-muted-foreground';
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

<Tabs.Root {value} onValueChange={(v) => v && onChange?.(v)} class="min-w-0 max-w-full self-end">
	<ScrollArea.Root orientation="horizontal" class="w-full">
		<Tabs.List variant="line" class="h-10 w-full justify-start">
			{#each tabs as tab (tab.key)}
				{#if tab.href}
					<Tabs.Trigger value={tab.key} class="flex-none px-3">
						{#snippet child({ props }: { props: Record<string, unknown> })}
							<a {...props} href={safeHref(tab.href)}>{@render body(tab)}</a>
						{/snippet}
					</Tabs.Trigger>
				{:else}
					<Tabs.Trigger value={tab.key} class="flex-none px-3">{@render body(tab)}</Tabs.Trigger>
				{/if}
			{/each}
		</Tabs.List>
	</ScrollArea.Root>
</Tabs.Root>
