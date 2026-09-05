<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Check from '@lucide/svelte/icons/check';
	import Tag from '@lucide/svelte/icons/tag';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { targetsApi } from '$lib/api/targets';
	import { tagsApi } from '$lib/api/tags';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { toast } from 'svelte-sonner';
	import type { TagSummary } from '$lib/types/target';

	interface Props {
		targetId: string;
		currentTags: TagSummary[];
		maxVisible?: number;
		onChange?: (patch: { tags: TagSummary[] }) => void;
	}

	let { targetId, currentTags, maxVisible = 3, onChange }: Props = $props();

	function applyPatch(patch: { tags: TagSummary[] }) {
		targetsStore.optimisticUpdateTarget(targetId, patch);
		onChange?.(patch);
	}

	let open = $state(false);
	let searchValue = $state('');
	let isUpdating = $state(false);
	let showColorPicker = $state(false);
	let selectedColor = $state('#6366f1');

	const presetColors = [
		'#ef4444',
		'#f97316',
		'#eab308',
		'#22c55e',
		'#14b8a6',
		'#3b82f6',
		'#6366f1',
		'#a855f7',
		'#ec4899',
		'#64748b'
	];

	let availableTags = $derived(
		targetsStore.tags.map((t) => ({
			id: t.id,
			name: t.name,
			slug: t.slug,
			color: t.color
		}))
	);

	let appliedIds = $derived(new Set(currentTags.map((t) => t.id)));

	let filteredTags = $derived(
		searchValue.trim()
			? availableTags.filter((t) => t.name.toLowerCase().includes(searchValue.toLowerCase()))
			: availableTags
	);

	let showCreateOption = $derived(
		searchValue.trim() !== '' &&
			!availableTags.some((t) => t.name.toLowerCase() === searchValue.toLowerCase())
	);

	let visibleTags = $derived(currentTags.slice(0, maxVisible));
	let overflowTags = $derived(currentTags.slice(maxVisible));
	let hasOverflow = $derived(overflowTags.length > 0);

	async function toggleTag(tag: TagSummary) {
		const isApplied = appliedIds.has(tag.id);
		const newTags = isApplied ? currentTags.filter((t) => t.id !== tag.id) : [...currentTags, tag];
		const newTagNames = newTags.map((t) => t.name);

		applyPatch({ tags: newTags });

		try {
			await targetsApi.update(targetId, { tag_names: newTagNames });
		} catch {
			applyPatch({ tags: currentTags });
			toast.error('Failed to update tags');
		}
	}

	function handleStartCreate() {
		showColorPicker = true;
	}

	async function handleConfirmCreate() {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug || !searchValue.trim()) return;

		const tagName = searchValue.trim();
		isUpdating = true;

		try {
			const newTag = await tagsApi.create({
				name: tagName,
				color: selectedColor,
				project_slug: projectSlug
			});

			const newTagSummary = {
				id: newTag.id,
				name: newTag.name,
				slug: newTag.slug,
				color: newTag.color
			};
			applyPatch({
				tags: [...currentTags, newTagSummary]
			});

			await Promise.all([
				targetsApi.update(targetId, { tag_names: [...currentTags.map((t) => t.name), tagName] }),
				targetsStore.fetchTags()
			]);

			searchValue = '';
			showColorPicker = false;
			selectedColor = '#6366f1';
			toast.success('Tag created and applied');
		} catch {
			toast.error('Failed to create tag');
		} finally {
			isUpdating = false;
		}
	}

	function handleCancelCreate() {
		showColorPicker = false;
	}

	function handleOpenChange(isOpen: boolean) {
		open = isOpen;
		if (!isOpen) {
			searchValue = '';
			showColorPicker = false;
		}
	}
</script>

<div class="flex items-center gap-1.5 min-w-0">
	{#if visibleTags.length > 0}
		{#each visibleTags as tag (tag.id)}
			<Badge
				class="text-xs font-normal border shrink-0"
				style="background-color: {tag.color}10; color: {tag.color}; border-color: {tag.color}30;"
			>
				{tag.name}
			</Badge>
		{/each}

		{#if hasOverflow}
			<HoverCard.Root>
				<HoverCard.Trigger>
					<Badge variant="outline" class="text-xs font-normal shrink-0 cursor-default">
						+{overflowTags.length}
					</Badge>
				</HoverCard.Trigger>
				<HoverCard.Content class="w-auto max-w-[280px] p-3" align="start">
					<div class="flex flex-wrap gap-1.5">
						{#each overflowTags as tag (tag.id)}
							<Badge
								class="text-xs font-normal border"
								style="background-color: {tag.color}10; color: {tag.color}; border-color: {tag.color}30;"
							>
								{tag.name}
							</Badge>
						{/each}
					</div>
				</HoverCard.Content>
			</HoverCard.Root>
		{/if}
	{/if}

	<Popover.Root {open} onOpenChange={handleOpenChange}>
		<Popover.Trigger>
			{#snippet child({ props })}
				{#if currentTags.length === 0}
					<button
						{...props}
						class="inline-flex items-center gap-1 text-xs text-muted-foreground/60 hover:text-muted-foreground border border-dashed border-border/60 hover:border-border rounded-md px-2 py-0.5 transition-colors cursor-pointer"
					>
						<Plus class="h-3 w-3" />
						Tag
					</button>
				{:else}
					<Tooltip.Root>
						<Tooltip.Trigger>
							<button
								{...props}
								class="inline-flex items-center justify-center h-5 w-5 rounded-full text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted transition-colors cursor-pointer shrink-0"
							>
								<Plus class="h-3 w-3" />
							</button>
						</Tooltip.Trigger>
						<Tooltip.Content>
							<p>Manage tags</p>
						</Tooltip.Content>
					</Tooltip.Root>
				{/if}
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-[240px] p-0" align="start">
			{#if showColorPicker}
				<div class="p-3 space-y-3">
					<p class="text-sm font-medium truncate">
						Pick a color for "<span class="text-primary">{searchValue}</span>"
					</p>
					<div class="flex flex-wrap gap-2">
						{#each presetColors as color (color)}
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
						<Button variant="ghost" size="sm" onclick={handleCancelCreate} disabled={isUpdating}>
							Cancel
						</Button>
						<Button size="sm" onclick={handleConfirmCreate} disabled={isUpdating} class="gap-1.5">
							<span class="h-2.5 w-2.5 rounded-full" style="background-color: {selectedColor}"
							></span>
							Create & apply
						</Button>
					</div>
				</div>
			{:else}
				<Command.Root shouldFilter={false}>
					<Command.Input placeholder="Search or create tags…" bind:value={searchValue} />
					<Command.List>
						<Command.Empty>
							{#if !showCreateOption}
								<div class="flex flex-col items-center gap-1 py-2">
									<Tag class="h-4 w-4 text-muted-foreground" />
									<span class="text-sm text-muted-foreground">No tags found</span>
								</div>
							{/if}
						</Command.Empty>
						<Command.Group>
							{#each filteredTags as tag (tag.id)}
								{@const isApplied = appliedIds.has(tag.id)}
								<Command.Item
									value={tag.id}
									onSelect={() => toggleTag(tag)}
									class="flex items-center gap-2"
									disabled={isUpdating}
								>
									<span
										class="h-2.5 w-2.5 rounded-full shrink-0"
										style="background-color: {tag.color}"
									></span>
									<span class="flex-1 truncate">{tag.name}</span>
									{#if isApplied}
										<Check class="h-4 w-4 text-primary shrink-0" />
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
									<span>Create "<span class="font-medium">{searchValue}</span>"</span>
								</Command.Item>
							</Command.Group>
						{/if}
					</Command.List>
				</Command.Root>
			{/if}
		</Popover.Content>
	</Popover.Root>
</div>
