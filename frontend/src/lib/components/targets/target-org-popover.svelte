<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Check from '@lucide/svelte/icons/check';
	import Building2 from '@lucide/svelte/icons/building-2';
	import { Badge } from '$lib/components/ui/badge';
	import * as Popover from '$lib/components/ui/popover';
	import * as Command from '$lib/components/ui/command';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { targetsApi } from '$lib/api/targets';
	import { organizationsApi } from '$lib/api/organizations';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { toast } from 'svelte-sonner';
	import type { OrganizationSummary } from '$lib/types/target';

	interface Props {
		targetId: string;
		currentOrgs: OrganizationSummary[];
		maxVisible?: number;
	}

	let { targetId, currentOrgs, maxVisible = 2 }: Props = $props();

	let open = $state(false);
	let searchValue = $state('');
	let isUpdating = $state(false);

	let availableOrgs = $derived(
		targetsStore.organizations.map((o) => ({
			id: o.id,
			name: o.name,
			slug: o.slug
		}))
	);

	let appliedIds = $derived(new Set(currentOrgs.map((o) => o.id)));

	let filteredOrgs = $derived(
		searchValue.trim()
			? availableOrgs.filter((o) => o.name.toLowerCase().includes(searchValue.toLowerCase()))
			: availableOrgs
	);

	let showCreateOption = $derived(
		searchValue.trim() !== '' &&
			!availableOrgs.some((o) => o.name.toLowerCase() === searchValue.toLowerCase())
	);

	let visibleOrgs = $derived(currentOrgs.slice(0, maxVisible));
	let overflowOrgs = $derived(currentOrgs.slice(maxVisible));
	let hasOverflow = $derived(overflowOrgs.length > 0);

	async function toggleOrg(org: OrganizationSummary) {
		const isApplied = appliedIds.has(org.id);
		const newOrgs = isApplied ? currentOrgs.filter((o) => o.id !== org.id) : [...currentOrgs, org];
		const newOrgNames = newOrgs.map((o) => o.name);

		targetsStore.optimisticUpdateTarget(targetId, { organizations: newOrgs });

		try {
			await targetsApi.update(targetId, { organization_names: newOrgNames });
		} catch {
			targetsStore.optimisticUpdateTarget(targetId, { organizations: currentOrgs });
			toast.error('Failed to update organizations');
		}
	}

	async function handleCreate() {
		const projectSlug = projectsStore.activeProject?.slug;
		if (!projectSlug || !searchValue.trim()) return;

		const orgName = searchValue.trim();
		isUpdating = true;

		try {
			const newOrg = await organizationsApi.create({ name: orgName, project_slug: projectSlug });

			const newOrgSummary = { id: newOrg.id, name: newOrg.name, slug: newOrg.slug };
			targetsStore.optimisticUpdateTarget(targetId, {
				organizations: [...currentOrgs, newOrgSummary]
			});

			await Promise.all([
				targetsApi.update(targetId, {
					organization_names: [...currentOrgs.map((o) => o.name), orgName]
				}),
				targetsStore.fetchOrganizations()
			]);

			searchValue = '';
			toast.success('Organization created and applied');
		} catch {
			toast.error('Failed to create organization');
		} finally {
			isUpdating = false;
		}
	}

	function handleOpenChange(isOpen: boolean) {
		open = isOpen;
		if (!isOpen) searchValue = '';
	}
</script>

<div class="flex items-center gap-1.5 min-w-0">
	{#if visibleOrgs.length > 0}
		{#each visibleOrgs as org (org.id)}
			<Badge variant="outline" class="text-xs font-normal gap-1 max-w-[100px] shrink-0">
				<Building2 class="h-3 w-3 shrink-0" />
				<span class="truncate">{org.name}</span>
			</Badge>
		{/each}

		{#if hasOverflow}
			<HoverCard.Root>
				<HoverCard.Trigger>
					<Badge variant="outline" class="text-xs font-normal shrink-0 cursor-default">
						+{overflowOrgs.length}
					</Badge>
				</HoverCard.Trigger>
				<HoverCard.Content class="w-auto max-w-[280px] p-3" align="start">
					<div class="flex flex-wrap gap-1.5">
						{#each overflowOrgs as org (org.id)}
							<Badge variant="outline" class="text-xs font-normal gap-1">
								<Building2 class="h-3 w-3 shrink-0" />
								{org.name}
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
				{#if currentOrgs.length === 0}
					<button
						{...props}
						class="inline-flex items-center gap-1 text-xs text-muted-foreground/60 hover:text-muted-foreground border border-dashed border-border/60 hover:border-border rounded-md px-2 py-0.5 transition-colors cursor-pointer"
					>
						<Plus class="h-3 w-3" />
						Org
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
							<p>Manage organizations</p>
						</Tooltip.Content>
					</Tooltip.Root>
				{/if}
			{/snippet}
		</Popover.Trigger>
		<Popover.Content class="w-[240px] p-0" align="start">
			<Command.Root shouldFilter={false}>
				<Command.Input placeholder="Search or create orgs..." bind:value={searchValue} />
				<Command.List>
					<Command.Empty>
						{#if !showCreateOption}
							<div class="flex flex-col items-center gap-1 py-2">
								<Building2 class="h-4 w-4 text-muted-foreground" />
								<span class="text-sm text-muted-foreground">No organizations found</span>
							</div>
						{/if}
					</Command.Empty>
					<Command.Group>
						{#each filteredOrgs as org (org.id)}
							{@const isApplied = appliedIds.has(org.id)}
							<Command.Item
								value={org.id}
								onSelect={() => toggleOrg(org)}
								class="flex items-center gap-2"
								disabled={isUpdating}
							>
								<Building2 class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
								<span class="flex-1 truncate">{org.name}</span>
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
								onSelect={handleCreate}
								class="flex items-center gap-2 text-primary"
								disabled={isUpdating}
							>
								<Plus class="h-4 w-4" />
								<span>Create "<span class="font-medium">{searchValue}</span>"</span>
							</Command.Item>
						</Command.Group>
					{/if}
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
</div>
