<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import FolderIcon from '@lucide/svelte/icons/folder';
	import CheckIcon from '@lucide/svelte/icons/check';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import AddProjectModal from '$lib/components/modals/add-project-modal.svelte';
	import ProjectIcon from '../project-icons.svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { ROUTES } from '$lib/config/routes';

	const sidebar = useSidebar();

	let activeProject = $derived(projectsStore.activeProject);
	let projects = $derived(projectsStore.projects);
	let isLoading = $derived(projectsStore.isLoading);

	let showAddModal = $state(false);

	const DETAIL_LIST_REDIRECTS: { match: RegExp; list: string }[] = [
		{ match: /^\/targets\/[^/]+/, list: ROUTES.targets },
		{ match: /^\/automation\/engines\/[^/]+/, list: ROUTES.engines },
		{ match: /^\/automation\/contexts\/[^/]+/, list: ROUTES.contexts }
	];

	function handleProjectSelect(project: (typeof projects)[0]) {
		if (project.id === activeProject?.id) return;
		projectsStore.setActiveProject(project);

		const path = page.url.pathname;
		const redirect = DETAIL_LIST_REDIRECTS.find((r) => r.match.test(path));
		if (redirect) goto(redirect.list);
	}
</script>

<AddProjectModal bind:open={showAddModal} />

<Sidebar.Menu>
	<Sidebar.MenuItem>
		{#if isLoading}
			<Sidebar.MenuButton size="lg" disabled>
				<div
					class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg"
				>
					<FolderIcon class="size-4 animate-pulse" />
				</div>
				<div class="grid flex-1 text-start text-sm leading-tight">
					<span class="truncate font-medium">Loading…</span>
				</div>
			</Sidebar.MenuButton>
		{:else if !activeProject}
			<Sidebar.MenuButton size="lg" onclick={() => (showAddModal = true)}>
				<div
					class="flex aspect-square size-8 items-center justify-center rounded-lg border border-dashed"
				>
					<PlusIcon class="size-4" />
				</div>
				<div class="grid flex-1 text-start text-sm leading-tight">
					<span class="truncate font-medium">Create project</span>
					<span class="truncate text-xs text-muted-foreground">Get started</span>
				</div>
			</Sidebar.MenuButton>
		{:else}
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Sidebar.MenuButton
							{...props}
							size="lg"
							class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
						>
							<div
								class="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg"
							>
								<ProjectIcon project={activeProject} class="size-4" />
							</div>
							<div class="grid flex-1 text-start text-sm leading-tight">
								<span class="truncate font-medium">
									{activeProject.name}
								</span>
							</div>
							<ChevronsUpDownIcon class="ms-auto" />
						</Sidebar.MenuButton>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content
					class="w-(--bits-dropdown-menu-anchor-width) min-w-56 rounded-lg"
					align="start"
					side={sidebar.isMobile ? 'bottom' : 'right'}
					sideOffset={4}
				>
					<DropdownMenu.Label class="text-muted-foreground text-xs">Projects</DropdownMenu.Label>

					{#each projects as project (project.id)}
						<DropdownMenu.Item onSelect={() => handleProjectSelect(project)} class="gap-2 p-2">
							<div class="flex size-6 items-center justify-center rounded-md border">
								<ProjectIcon {project} class="size-4" />
							</div>
							<span class="flex-1 truncate">{project.name}</span>
							{#if project.id === activeProject?.id}
								<CheckIcon class="size-4 text-muted-foreground" />
							{/if}
						</DropdownMenu.Item>
					{/each}

					<DropdownMenu.Separator />

					<DropdownMenu.Item class="gap-2 p-2" onSelect={() => (showAddModal = true)}>
						<div class="flex size-6 items-center justify-center rounded-md border bg-transparent">
							<PlusIcon class="size-4" />
						</div>
						<span class="text-muted-foreground font-medium">Add project</span>
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		{/if}
	</Sidebar.MenuItem>
</Sidebar.Menu>
