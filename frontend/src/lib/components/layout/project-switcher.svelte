<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import ChevronsUpDown from 'lucide-svelte/icons/chevrons-up-down';
	import Plus from 'lucide-svelte/icons/plus';
	import Building2 from 'lucide-svelte/icons/building-2';
	import Shield from 'lucide-svelte/icons/shield';
	import Bug from 'lucide-svelte/icons/bug';
	import FolderKanban from 'lucide-svelte/icons/folder-kanban';
	import { projectsStore } from '$lib/stores/projects.svelte';

	const sidebar = useSidebar();

	const iconMap: Record<string, typeof Building2> = {
		Building2,
		Shield,
		Bug,
		FolderKanban
	};

	function getIcon(iconName: string) {
		return iconMap[iconName] || FolderKanban;
	}

	function handleAddProject() {
		// TODO: Open add project modal
		console.log('Add project clicked');
	}
</script>

<Sidebar.Menu>
	<Sidebar.MenuItem>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Sidebar.MenuButton
						{...props}
						size="lg"
						class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
					>
						{#if projectsStore.activeProject}
							{@const IconComponent = getIcon(projectsStore.activeProject.icon)}
							<div
								class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg"
							>
								<IconComponent class="size-4" />
							</div>
							<div class="grid flex-1 text-start text-sm leading-tight">
								<span class="truncate font-medium">
									{projectsStore.activeProject.name}
								</span>
								<span class="truncate text-xs text-muted-foreground">
									{projectsStore.activeProject.targets_count ?? 0} targets
								</span>
							</div>
						{:else}
							<div
								class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg"
							>
								<FolderKanban class="size-4" />
							</div>
							<div class="grid flex-1 text-start text-sm leading-tight">
								<span class="truncate font-medium">No Project</span>
								<span class="truncate text-xs">Select a project</span>
							</div>
						{/if}
						<ChevronsUpDown class="ms-auto size-4" />
					</Sidebar.MenuButton>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content
				class="w-[--bits-dropdown-menu-anchor-width] min-w-56 rounded-lg"
				align="start"
				side={sidebar.isMobile ? 'bottom' : 'right'}
				sideOffset={4}
			>
				<DropdownMenu.Label class="text-muted-foreground text-xs">Projects</DropdownMenu.Label>
				{#each projectsStore.projects as project, index (project.id)}
					{@const IconComponent = getIcon(project.icon)}
					<DropdownMenu.Item
						onSelect={() => projectsStore.setActiveProject(project)}
						class="gap-2 p-2"
					>
						<div class="flex size-6 items-center justify-center rounded-md border">
							<IconComponent class="size-3.5 shrink-0" />
						</div>
						<div class="flex flex-col">
							<span>{project.name}</span>
							{#if project.description}
								<span class="text-xs text-muted-foreground">{project.description}</span>
							{/if}
						</div>
						<DropdownMenu.Shortcut>⌘{index + 1}</DropdownMenu.Shortcut>
					</DropdownMenu.Item>
				{/each}
				<DropdownMenu.Separator />
				<DropdownMenu.Item class="gap-2 p-2" onSelect={handleAddProject}>
					<div class="flex size-6 items-center justify-center rounded-md border bg-transparent">
						<Plus class="size-4" />
					</div>
					<div class="text-muted-foreground font-medium">Add project</div>
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</Sidebar.MenuItem>
</Sidebar.Menu>