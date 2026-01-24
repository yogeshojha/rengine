<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import ProjectSwitcher from './project-switcher.svelte';
	import NavSearch from './nav-search.svelte';
	import NavMain from './nav-main.svelte';
	import NavToolbox from './nav-toolbox.svelte';
	import NavQuickActions from './nav-quick-actions.svelte';
	import NavDocs from './nav-docs.svelte';
	import NavUser from './nav-user.svelte';
	import { navMain, toolboxItems, quickActions, documentationLink } from '$lib/config/navigation';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { onMount } from 'svelte';
	import type { ComponentProps } from 'svelte';

	let {
		ref = $bindable(null),
		collapsible = 'icon',
		...restProps
	}: ComponentProps<typeof Sidebar.Root> = $props();

	// Initialize projects store
	onMount(() => {
		projectsStore.init();
	});
</script>

<Sidebar.Root {collapsible} {...restProps} bind:ref>
	<Sidebar.Header>
		<ProjectSwitcher />
		<NavSearch />
	</Sidebar.Header>

	<Separator class="my-2" />

	<Sidebar.Content>
		<NavMain items={navMain} />
		<NavQuickActions actions={quickActions} />
		<NavToolbox items={toolboxItems} />
		<NavDocs link={documentationLink} />
	</Sidebar.Content>

	<Sidebar.Footer>
		<NavUser />
	</Sidebar.Footer>

	<Sidebar.Rail />
</Sidebar.Root>