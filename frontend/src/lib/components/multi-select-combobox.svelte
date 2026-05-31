<script lang="ts">
	import { X, Check, Plus, Search } from 'lucide-svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';

	interface Item {
		id: string;
		label: string;
		color?: string;
	}

	interface Props {
		items: Item[];
		selected: Item[];
		onSelect: (item: Item) => void;
		onRemove: (item: Item) => void;
		onCreate?: (value: string) => void;
		placeholder?: string;
		emptyText?: string;
		allowCreate?: boolean;
		showColors?: boolean;
	}

	let {
		items,
		selected,
		onSelect,
		onRemove,
		onCreate,
		placeholder = 'Search...',
		emptyText = 'No items found.',
		allowCreate = true,
		showColors = false
	}: Props = $props();

	let open = $state(false);
	let searchValue = $state('');

	let filteredItems = $derived(
		items.filter(
			(item) =>
				item.label.toLowerCase().includes(searchValue.toLowerCase()) &&
				!selected.some((s) => s.id === item.id)
		)
	);

	let showCreateOption = $derived(
		allowCreate &&
			searchValue.trim() !== '' &&
			!items.some((item) => item.label.toLowerCase() === searchValue.toLowerCase())
	);

	function handleSelect(item: Item) {
		onSelect(item);
		searchValue = '';
	}

	function handleCreate() {
		if (onCreate && searchValue.trim()) {
			onCreate(searchValue.trim());
			searchValue = '';
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && showCreateOption) {
			e.preventDefault();
			handleCreate();
		}
	}
</script>

<div class="space-y-2">
	<!-- Selected Items as Chips -->
	{#if selected.length > 0}
		<div class="flex flex-wrap gap-1.5">
			{#each selected as item}
				<Badge
					variant="secondary"
					class="gap-1 pr-1 font-normal"
					style={showColors && item.color
						? `background-color: ${item.color}15; color: ${item.color}; border: 1px solid ${item.color}30;`
						: ''}
				>
					{#if showColors && item.color}
						<span class="h-2 w-2 rounded-full shrink-0" style="background-color: {item.color}"
						></span>
					{/if}
					{item.label}
					<button
						type="button"
						class="ml-1 rounded-full hover:bg-foreground/10 p-0.5"
						onclick={() => onRemove(item)}
					>
						<X class="h-3 w-3" />
					</button>
				</Badge>
			{/each}
		</div>
	{/if}

	<!-- Combobox -->
	<Popover.Root bind:open>
		<Popover.Trigger class="w-full">
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					role="combobox"
					class="w-full justify-start text-muted-foreground font-normal h-9"
				>
					<Search class="h-4 w-4 mr-2 shrink-0" />
					{placeholder}
				</Button>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-[--radix-popover-trigger-width] p-0" align="start">
			<Command.Root shouldFilter={false}>
				<Command.Input {placeholder} bind:value={searchValue} onkeydown={handleKeydown} />
				<Command.List>
					<Command.Empty>
						{#if !showCreateOption}
							{emptyText}
						{/if}
					</Command.Empty>
					<Command.Group>
						{#each filteredItems as item}
							<Command.Item
								value={item.id}
								onSelect={() => handleSelect(item)}
								class="flex items-center gap-2"
							>
								{#if showColors && item.color}
									<span
										class="h-2.5 w-2.5 rounded-full shrink-0"
										style="background-color: {item.color}"
									></span>
								{/if}
								<span class="flex-1 truncate">{item.label}</span>
								{#if selected.some((s) => s.id === item.id)}
									<Check class="h-4 w-4 text-primary" />
								{/if}
							</Command.Item>
						{/each}
					</Command.Group>

					{#if showCreateOption}
						<Command.Group>
							<Command.Item
								value="__create__"
								onSelect={handleCreate}
								class="flex items-center gap-2 text-primary"
							>
								<Plus class="h-4 w-4" />
								<span>Create "{searchValue}"</span>
							</Command.Item>
						</Command.Group>
					{/if}
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
</div>
