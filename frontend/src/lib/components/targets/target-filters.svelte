<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Tag from '@lucide/svelte/icons/tag';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Separator } from '$lib/components/ui/separator';
	import type { OrganizationSummary, TagSummary } from '$lib/types/target';

	interface Props {
		searchQuery: string;
		onSearchChange: (query: string) => void;
		organizations: OrganizationSummary[];
		selectedOrganizations: string[];
		onOrganizationToggle: (orgId: string) => void;
		tags: TagSummary[];
		selectedTags: string[];
		onTagToggle: (tagId: string) => void;
		onClearFilters: () => void;
	}

	let {
		searchQuery,
		onSearchChange,
		organizations,
		selectedOrganizations,
		onOrganizationToggle,
		tags,
		selectedTags,
		onTagToggle,
		onClearFilters
	}: Props = $props();

	let orgPopoverOpen = $state(false);
	let tagPopoverOpen = $state(false);

	let hasActiveFilters = $derived(
		selectedOrganizations.length > 0 || selectedTags.length > 0 || searchQuery.trim() !== ''
	);

	let activeFilterCount = $derived(selectedOrganizations.length + selectedTags.length);
</script>

<div class="flex flex-wrap items-center gap-3 gap-y-2">
	<div class="relative flex-1 min-w-0 sm:max-w-sm">
		<Search class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
		<Input
			type="text"
			placeholder="Search targets..."
			class="pl-9 h-9"
			value={searchQuery}
			oninput={(e) => onSearchChange(e.currentTarget.value)}
		/>
		{#if searchQuery}
			<Button
				variant="ghost"
				size="icon"
				class="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
				onclick={() => onSearchChange('')}
			>
				<X class="h-3 w-3" />
			</Button>
		{/if}
	</div>

	<Popover.Root bind:open={orgPopoverOpen}>
		<Popover.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					size="sm"
					class="h-9 gap-2 {selectedOrganizations.length > 0
						? 'border-primary/50 bg-primary/5'
						: ''}"
				>
					<Building2 class="h-4 w-4" />
					<span>Organizations</span>
					{#if selectedOrganizations.length > 0}
						<Badge variant="secondary" class="h-5 px-1.5 text-xs">
							{selectedOrganizations.length}
						</Badge>
					{/if}
				</Button>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-56 p-0" align="start">
			<Command.Root>
				<Command.Input placeholder="Search organizations..." />
				<Command.List>
					<Command.Empty>No organizations found.</Command.Empty>
					<Command.Group>
						{#each organizations as org (org.id)}
							<Command.Item
								onSelect={() => onOrganizationToggle(org.id)}
								class="flex items-center gap-2"
							>
								<Checkbox checked={selectedOrganizations.includes(org.id)} />
								<span class="truncate">{org.name}</span>
							</Command.Item>
						{/each}
					</Command.Group>
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>

	<Popover.Root bind:open={tagPopoverOpen}>
		<Popover.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					size="sm"
					class="h-9 gap-2 {selectedTags.length > 0 ? 'border-primary/50 bg-primary/5' : ''}"
				>
					<Tag class="h-4 w-4" />
					<span>Tags</span>
					{#if selectedTags.length > 0}
						<Badge variant="secondary" class="h-5 px-1.5 text-xs">
							{selectedTags.length}
						</Badge>
					{/if}
				</Button>
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-56 p-0" align="start">
			<Command.Root>
				<Command.Input placeholder="Search tags..." />
				<Command.List>
					<Command.Empty>No tags found.</Command.Empty>
					<Command.Group>
						{#each tags as tag (tag.id)}
							<Command.Item onSelect={() => onTagToggle(tag.id)} class="flex items-center gap-2">
								<Checkbox checked={selectedTags.includes(tag.id)} />
								<span
									class="h-2.5 w-2.5 rounded-full shrink-0"
									style="background-color: {tag.color}"
								></span>
								<span class="truncate">{tag.name}</span>
							</Command.Item>
						{/each}
					</Command.Group>
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>

	{#if hasActiveFilters}
		<Separator orientation="vertical" class="h-6" />
		<Button
			variant="ghost"
			size="sm"
			class="h-9 gap-2 text-muted-foreground"
			onclick={onClearFilters}
		>
			<X class="h-4 w-4" />
			Clear filters
			{#if activeFilterCount > 0}
				<Badge variant="secondary" class="h-5 px-1.5 text-xs">
					{activeFilterCount}
				</Badge>
			{/if}
		</Button>
	{/if}
</div>
