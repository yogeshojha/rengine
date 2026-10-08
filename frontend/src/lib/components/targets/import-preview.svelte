<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import EmptyState from '$lib/components/empty-state.svelte';
	import * as Tabs from '$lib/components/ui/tabs';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import CircleMinus from '@lucide/svelte/icons/circle-minus';
	import Tag from '@lucide/svelte/icons/tag';
	import Landmark from '@lucide/svelte/icons/landmark';
	import { formatTargetType, type TargetPreviewItem } from '$lib/types/target';
	import { TARGET_TYPE_ICONS_COMPACT } from '$lib/config/icons';

	interface Props {
		items: TargetPreviewItem[];
	}

	let { items }: Props = $props();

	type Group = 'all' | 'ready' | 'skipped' | 'invalid';

	const GROUPS: { key: Group; label: string }[] = [
		{ key: 'all', label: 'All' },
		{ key: 'ready', label: 'Ready' },
		{ key: 'skipped', label: 'Skipped' },
		{ key: 'invalid', label: 'Invalid' }
	];

	function groupOf(item: TargetPreviewItem): Exclude<Group, 'all'> {
		if (item.error) return 'invalid';
		return item.skipped ? 'skipped' : 'ready';
	}

	let group = $state<Group>('all');

	// rows keep their place in the input, which can repeat a value
	let rows = $derived(items.map((item, i) => ({ item, i, group: groupOf(item) })));
	let counts = $derived(
		rows.reduce<Record<Group, number>>(
			(acc, row) => {
				acc[row.group] += 1;
				return acc;
			},
			{ all: rows.length, ready: 0, skipped: 0, invalid: 0 }
		)
	);
	let shown = $derived(group === 'all' ? rows : rows.filter((row) => row.group === group));
</script>

<div class="flex flex-col gap-3">
	<Tabs.Root bind:value={group}>
		<Tabs.List variant="line">
			{#each GROUPS as { key, label } (key)}
				<Tabs.Trigger value={key} class="flex-none px-3">
					{label}
					<span class="text-xs tabular-nums text-muted-foreground">
						{counts[key].toLocaleString()}
					</span>
				</Tabs.Trigger>
			{/each}
		</Tabs.List>
	</Tabs.Root>

	{#if shown.length === 0}
		<EmptyState
			compact
			title={group === 'all' ? 'No targets' : `No ${group} targets`}
			class="rounded-md border"
		/>
	{:else}
		<ul class="divide-y rounded-md border">
			{#each shown as { item, i, group: kind } (i)}
				<li class="flex flex-col gap-1.5 p-3 {kind === 'invalid' ? 'bg-destructive/5' : ''}">
					<div class="flex min-w-0 items-center gap-2">
						{#if item.target_type}
							{@const TypeIcon = TARGET_TYPE_ICONS_COMPACT[item.target_type]}
							<TypeIcon class="size-3.5 shrink-0 text-muted-foreground" />
						{/if}
						<code
							class="min-w-0 truncate font-mono text-sm {kind === 'invalid'
								? 'text-destructive'
								: kind === 'skipped'
									? 'text-muted-foreground'
									: ''}"
							title={item.target_value}
						>
							{item.target_value}
						</code>
						{#if item.target_type}
							<span class="shrink-0 text-xs text-muted-foreground">
								{formatTargetType(item.target_type)}
							</span>
						{/if}
					</div>

					{#if item.display_name}
						<p class="pl-5 text-xs text-muted-foreground">{item.display_name}</p>
					{/if}

					{#if item.organizations?.length || item.tags?.length}
						<div class="flex flex-wrap items-center gap-x-3 gap-y-1 pl-5">
							{#if item.organizations?.length}
								<span class="flex items-center gap-1 text-xs text-muted-foreground">
									<Landmark class="size-3" />
									{item.organizations.join(', ')}
								</span>
							{/if}
							{#if item.tags?.length}
								<span class="flex flex-wrap items-center gap-1.5">
									<Tag class="size-3 text-muted-foreground" />
									{#each item.tags as tag (tag)}
										<Badge variant="secondary" class="font-normal">{tag}</Badge>
									{/each}
								</span>
							{/if}
						</div>
					{/if}

					{#if item.error}
						<p class="flex items-center gap-1.5 pl-5 text-xs text-destructive">
							<CircleAlert class="size-3 shrink-0" />
							{item.error}
						</p>
					{:else if item.skipped}
						<p class="flex items-center gap-1.5 pl-5 text-xs text-muted-foreground">
							<CircleMinus class="size-3 shrink-0" />
							{item.skipped}
						</p>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>
