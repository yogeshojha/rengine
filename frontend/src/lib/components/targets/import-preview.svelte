<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import * as Tabs from '$lib/components/ui/tabs';
	import { CircleAlert, Tag, Landmark } from 'lucide-svelte';
	import { TargetType, formatTargetType } from '$lib/types/target';
	import { TARGET_TYPE_ICONS_COMPACT } from '$lib/config/icons';

	interface PreviewItem {
		target_value: string;
		target_type?: TargetType | null;
		tags?: string[];
		organizations?: string[];
		display_name?: string | null;
		error?: string;
	}

	interface Props {
		items: PreviewItem[];
		maxHeight?: string;
	}

	let { items, maxHeight = '400px' }: Props = $props();

	let filterTab = $state<'all' | 'valid' | 'invalid'>('all');

	let validItems = $derived(items.filter((item) => !item.error));
	let invalidItems = $derived(items.filter((item) => item.error));

	let filteredItems = $derived.by(() => {
		if (filterTab === 'valid') return validItems;
		if (filterTab === 'invalid') return invalidItems;
		return items;
	});

	let validCount = $derived(validItems.length);
	let invalidCount = $derived(invalidItems.length);
</script>

<div class="space-y-3">
	<div class="flex items-center justify-between px-1">
		<span class="text-sm font-medium">{items.length} targets</span>

		<Tabs.Root bind:value={filterTab} class="w-auto">
			<Tabs.List class="h-8">
				<Tabs.Trigger value="all" class="text-xs h-7 px-3">
					All ({items.length})
				</Tabs.Trigger>
				<Tabs.Trigger value="valid" class="text-xs h-7 px-3">
					<div class="flex items-center gap-1.5">
						<div class="h-1.5 w-1.5 rounded-full bg-green-500"></div>
						Valid ({validCount})
					</div>
				</Tabs.Trigger>
				<Tabs.Trigger value="invalid" class="text-xs h-7 px-3">
					<div class="flex items-center gap-1.5">
						<div class="h-1.5 w-1.5 rounded-full bg-red-500"></div>
						Invalid ({invalidCount})
					</div>
				</Tabs.Trigger>
			</Tabs.List>
		</Tabs.Root>
	</div>

	<ScrollArea class="h-[400px] rounded-md border">
		<div class="divide-y">
			{#each filteredItems as item, i (i)}
				<div
					class="p-3 hover:bg-accent/50 transition-colors {item.error ? 'bg-destructive/5' : ''}"
				>
					<div class="space-y-1.5">
						<div class="flex items-center gap-2">
							{#if item.target_type}
								{@const TypeIcon = TARGET_TYPE_ICONS_COMPACT[item.target_type]}
								<TypeIcon class="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
							{/if}
							<code class="text-sm font-mono {item.error ? 'text-destructive' : ''}">
								{item.target_value}
							</code>
							{#if item.target_type}
								<span class="text-xs text-muted-foreground">
									{formatTargetType(item.target_type)}
								</span>
							{/if}
						</div>

						{#if item.display_name}
							<p class="text-xs text-muted-foreground pl-5">
								{item.display_name}
							</p>
						{/if}

						{#if (item.organizations && item.organizations.length > 0) || (item.tags && item.tags.length > 0)}
							<div class="flex items-center gap-3 pl-5">
								{#if item.organizations && item.organizations.length > 0}
									<div class="flex items-center gap-1 text-xs text-muted-foreground">
										<Landmark class="h-3 w-3" />
										<span>{item.organizations.join(', ')}</span>
									</div>
								{/if}

								{#if item.tags && item.tags.length > 0}
									<div class="flex items-center gap-1.5">
										<Tag class="h-3 w-3 text-muted-foreground" />
										{#each item.tags as tag}
											<Badge variant="secondary" class="text-[10px] px-1.5 py-0 h-4 font-normal">
												{tag}
											</Badge>
										{/each}
									</div>
								{/if}
							</div>
						{/if}

						{#if item.error}
							<div class="flex items-center gap-1.5 text-xs text-destructive pl-5">
								<CircleAlert class="h-3 w-3 flex-shrink-0" />
								{item.error}
							</div>
						{/if}
					</div>
				</div>
			{/each}

			{#if filteredItems.length === 0}
				<div class="p-8 text-center text-sm text-muted-foreground">
					No {filterTab} targets found
				</div>
			{/if}
		</div>
	</ScrollArea>
</div>
