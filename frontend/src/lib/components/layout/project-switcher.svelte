<script lang="ts">
	import * as DropdownMenu from "$lib/components/ui/dropdown-menu/index.js";
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import { useSidebar } from "$lib/components/ui/sidebar/index.js";
	import ChevronsUpDownIcon from "@lucide/svelte/icons/chevrons-up-down";
	import FolderIcon from "@lucide/svelte/icons/folder";
	import PlusIcon from "@lucide/svelte/icons/plus";
	import { projectsStore } from '$lib/stores/projects.svelte';

	const sidebar = useSidebar();

	let activeProject = $derived(projectsStore.activeProject);
    let projects = $derived(projectsStore.projects);
    let isLoading = $derived(projectsStore.isLoading);

	function handleProjectSelect(project: typeof projects[0]) {
        projectsStore.setActiveProject(project);
    }

	function handleAddProject() {
        // TODO: Open modal to create project
        console.log('Add project clicked');
    }
</script>

<Sidebar.Menu>
    <Sidebar.MenuItem>
        {#if isLoading}
            <!-- Loading state -->
            <Sidebar.MenuButton size="lg" disabled>
                <div class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg animate-pulse">
                    <FolderIcon class="size-4" />
                </div>
                <div class="grid flex-1 text-start text-sm leading-tight">
                    <span class="truncate font-medium">Loading...</span>
                </div>
            </Sidebar.MenuButton>
        {:else if !activeProject}
            <!-- No projects state -->
            <Sidebar.MenuButton size="lg" onclick={handleAddProject}>
                <div class="flex aspect-square size-8 items-center justify-center rounded-lg border border-dashed">
                    <PlusIcon class="size-4" />
                </div>
                <div class="grid flex-1 text-start text-sm leading-tight">
                    <span class="truncate font-medium">Create Project</span>
                    <span class="truncate text-xs text-muted-foreground">Get started</span>
                </div>
            </Sidebar.MenuButton>
        {:else}
            <!-- Normal dropdown -->
            <DropdownMenu.Root>
                <DropdownMenu.Trigger>
                    {#snippet child({ props })}
                        <Sidebar.MenuButton
                            {...props}
                            size="lg"
                            class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                        >
                            <div class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                                <FolderIcon class="size-4" />
                            </div>
                            <div class="grid flex-1 text-start text-sm leading-tight">
                                <span class="truncate font-medium">
                                    {activeProject.name}
                                </span>
                                <span class="truncate text-xs text-muted-foreground">
                                    {activeProject.slug}
                                </span>
                            </div>
                            <ChevronsUpDownIcon class="ms-auto" />
                        </Sidebar.MenuButton>
                    {/snippet}
                </DropdownMenu.Trigger>
                <DropdownMenu.Content
                    class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
                    align="start"
                    side={sidebar.isMobile ? "bottom" : "right"}
                    sideOffset={4}
                >
                    <DropdownMenu.Label class="text-muted-foreground text-xs">
                        Projects
                    </DropdownMenu.Label>

                    {#each projects as project (project.id)}
                        <DropdownMenu.Item
                            onSelect={() => handleProjectSelect(project)}
                            class="gap-2 p-2"
                        >
                            <div class="flex size-6 items-center justify-center rounded-md border">
                                <FolderIcon class="size-3.5 shrink-0" />
                            </div>
                            <div class="flex-1">
                                <div class="font-medium">{project.name}</div>
                            </div>
                            {#if project.id === activeProject?.id}
                                <span class="text-xs text-muted-foreground">Active</span>
                            {/if}
                        </DropdownMenu.Item>
                    {/each}

                    <DropdownMenu.Separator />

                    <DropdownMenu.Item class="gap-2 p-2" onSelect={handleAddProject}>
                        <div class="flex size-6 items-center justify-center rounded-md border bg-transparent">
                            <PlusIcon class="size-4" />
                        </div>
                        <div class="text-muted-foreground font-medium">Add project</div>
                    </DropdownMenu.Item>
                </DropdownMenu.Content>
            </DropdownMenu.Root>
        {/if}
    </Sidebar.MenuItem>
</Sidebar.Menu>
