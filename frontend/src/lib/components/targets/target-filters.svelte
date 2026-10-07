<script lang="ts">
	import Search from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';
	import Building2 from '@lucide/svelte/icons/building-2';
	import Tag from '@lucide/svelte/icons/tag';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import TargetLabelsDialog from './target-labels-dialog.svelte';
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
	}

	let {
		searchQuery,
		onSearchChange,
		organizations,
		selectedOrganizations,
		onOrganizationToggle,
		tags,
		selectedTags,
		onTagToggle
	}: Props = $props();

	let orgPopoverOpen = $state(false);
	let tagPopoverOpen = $state(false);
	let managing = $state<'tag' | 'organization' | null>(null);
	let manageKind = $state<'tag' | 'organization'>('tag');

	function manage(kind: 'tag' | 'organization') {
		orgPopoverOpen = false;
		tagPopoverOpen = false;
		manageKind = kind;
		managing = kind;
	}
</script>

<div class="flex flex-wrap items-center gap-3 gap-y-2">
	<InputGroup.Root class="w-auto min-w-0 flex-1 basis-full sm:max-w-sm sm:basis-0">
		<InputGroup.Addon><Search /></InputGroup.Addon>
		<InputGroup.Input
			id="target-search"
			type="text"
			placeholder="Search targets"
			aria-label="Search targets"
			value={searchQuery}
			oninput={(e) => onSearchChange(e.currentTarget.value)}
		/>
		{#if searchQuery}
			<InputGroup.Addon align="inline-end">
				<InputGroup.Button
					size="icon-xs"
					aria-label="Clear search"
					onclick={() => onSearchChange('')}
				>
					<X />
				</InputGroup.Button>
			</InputGroup.Addon>
		{/if}
	</InputGroup.Root>

	<Popover.Root bind:open={orgPopoverOpen}>
		<Popover.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					class={selectedOrganizations.length > 0 ? 'border-primary/50 bg-primary/5' : ''}
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
				<Command.Input placeholder="Search organizations" />
				<Command.List class="max-h-72">
					<Command.Empty>No organizations</Command.Empty>
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
			<div class="border-t p-1">
				<Button
					variant="ghost"
					size="sm"
					class="w-full justify-start"
					onclick={() => manage('organization')}
				>
					<Settings2 class="size-4" />
					Manage organizations
				</Button>
			</div>
		</Popover.Content>
	</Popover.Root>

	<Popover.Root bind:open={tagPopoverOpen}>
		<Popover.Trigger>
			{#snippet child({ props })}
				<Button
					{...props}
					variant="outline"
					class={selectedTags.length > 0 ? 'border-primary/50 bg-primary/5' : ''}
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
				<Command.Input placeholder="Search tags" />
				<Command.List class="max-h-72">
					<Command.Empty>No tags</Command.Empty>
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
			<div class="border-t p-1">
				<Button
					variant="ghost"
					size="sm"
					class="w-full justify-start"
					onclick={() => manage('tag')}
				>
					<Settings2 class="size-4" />
					Manage tags
				</Button>
			</div>
		</Popover.Content>
	</Popover.Root>
</div>

<TargetLabelsDialog
	kind={manageKind}
	open={managing !== null}
	onOpenChange={(open) => {
		if (!open) managing = null;
	}}
/>
