<script lang="ts">
	import { X, Check, Plus, Search } from 'lucide-svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';

	interface TagItem {
		id: string;
		label: string;
		color: string;
	}

	interface Props {
		items: TagItem[];
		selected: TagItem[];
		onSelect: (item: TagItem) => void;
		onRemove: (item: TagItem) => void;
		onCreate?: (label: string, color: string) => void;
		placeholder?: string;
	}

	let {
		items,
		selected,
		onSelect,
		onRemove,
		onCreate,
		placeholder = 'Search tags...'
	}: Props = $props();

	let open = $state(false);
	let searchValue = $state('');
	let showColorPicker = $state(false);
	let selectedColor = $state('#6366f1');

	const presetColors = [
		'#ef4444', // red
		'#f97316', // orange
		'#eab308', // yellow
		'#22c55e', // green
		'#14b8a6', // teal
		'#3b82f6', // blue
		'#6366f1', // indigo
		'#a855f7', // purple
		'#ec4899', // pink
		'#64748b' // slate
	];

	let filteredItems = $derived(
		items.filter(
			(item) =>
				item.label.toLowerCase().includes(searchValue.toLowerCase()) &&
				!selected.some((s) => s.id === item.id)
		)
	);

	let showCreateOption = $derived(
		searchValue.trim() !== '' &&
			!items.some((item) => item.label.toLowerCase() === searchValue.toLowerCase())
	);

	function handleSelect(item: TagItem) {
		onSelect(item);
		searchValue = '';
	}

	function handleStartCreate() {
		showColorPicker = true;
	}

	function handleConfirmCreate() {
		if (onCreate && searchValue.trim()) {
			onCreate(searchValue.trim(), selectedColor);
			searchValue = '';
			showColorPicker = false;
			selectedColor = '#6366f1';
		}
	}

	function handleCancelCreate() {
		showColorPicker = false;
	}
</script>

<div class="space-y-2">
	<!-- Selected Tags as Chips -->
	{#if selected.length > 0}
		<div class="flex flex-wrap gap-1.5">
			{#each selected as item}
				<Badge
					variant="secondary"
					class="gap-1.5 pr-1 font-normal border"
					style="background-color: {item.color}15; color: {item.color}; border-color: {item.color}30;"
				>
					<span class="h-2 w-2 rounded-full shrink-0" style="background-color: {item.color}"></span>
					{item.label}
					<button
						type="button"
						class="ml-0.5 rounded-full hover:bg-foreground/10 p-0.5"
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
			{#if showColorPicker}
				<!-- Color Picker View -->
				<div class="p-3 space-y-3">
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium">Pick a color for "{searchValue}"</span>
					</div>
					<div class="flex flex-wrap gap-2">
						{#each presetColors as color}
							<button
								type="button"
								class="h-6 w-6 rounded-full border-2 transition-transform hover:scale-110 {selectedColor ===
								color
									? 'border-foreground scale-110'
									: 'border-transparent'}"
								style="background-color: {color}"
								onclick={() => (selectedColor = color)}
							>
								{#if selectedColor === color}
									<Check class="h-3 w-3 text-white mx-auto" />
								{/if}
							</button>
						{/each}
					</div>
					<div class="flex items-center gap-2 pt-1">
						<Button variant="ghost" size="sm" onclick={handleCancelCreate}>Cancel</Button>
						<Button size="sm" onclick={handleConfirmCreate} class="gap-1.5">
							<span class="h-2.5 w-2.5 rounded-full" style="background-color: {selectedColor}"
							></span>
							Create tag
						</Button>
					</div>
				</div>
			{:else}
				<!-- Search View -->
				<Command.Root shouldFilter={false}>
					<Command.Input {placeholder} bind:value={searchValue} />
					<Command.List>
						<Command.Empty>
							{#if !showCreateOption}
								No tags found.
							{/if}
						</Command.Empty>
						<Command.Group>
							{#each filteredItems as item}
								<Command.Item
									value={item.id}
									onSelect={() => handleSelect(item)}
									class="flex items-center gap-2"
								>
									<span
										class="h-2.5 w-2.5 rounded-full shrink-0"
										style="background-color: {item.color}"
									></span>
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
									onSelect={handleStartCreate}
									class="flex items-center gap-2 text-primary"
								>
									<Plus class="h-4 w-4" />
									<span>Create "{searchValue}"</span>
								</Command.Item>
							</Command.Group>
						{/if}
					</Command.List>
				</Command.Root>
			{/if}
		</Popover.Content>
	</Popover.Root>
</div>
