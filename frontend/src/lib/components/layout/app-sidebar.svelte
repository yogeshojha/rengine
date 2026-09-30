<script lang="ts">
	import NavMain from './nav-main.svelte';
	import NavUser from './nav-user.svelte';
	import ProjectSwitcher from './project-switcher.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { untrack, type ComponentProps } from 'svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { whatsNewStore } from '$lib/stores/whats-new.svelte';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { sidebarLayout } from '$lib/stores/sidebar-layout.svelte';
	import { useSidebarNav } from './sidebar-nav.svelte';

	let {
		ref = $bindable(null),
		collapsible = 'icon',
		...restProps
	}: ComponentProps<typeof Sidebar.Root> = $props();

	const nav = useSidebarNav();

	$effect(() => {
		const id = projectsStore.activeProject?.id;
		if (id) untrack(() => void whatsNewStore.fetch(id));
	});

	$effect(() => {
		if (nav.bountyOn) untrack(() => void bountyVocabulary.load());
	});

	$effect(() => {
		void auth.user?.id;
		untrack(() => sidebarLayout.load());
	});

	const userData = $derived({
		name: auth.user?.username ?? 'Unknown user',
		email: auth.user?.email ?? 'admin@rengine.local',
		is_superuser: auth.user?.is_superuser ?? false
	});
</script>

<Sidebar.Root bind:ref {collapsible} variant="inset" {...restProps}>
	<Sidebar.Header>
		<ProjectSwitcher />
	</Sidebar.Header>
	<Sidebar.Content class="overflow-hidden">
		<ScrollArea class="min-h-0 flex-1">
			<NavMain groups={nav.main} />
		</ScrollArea>
	</Sidebar.Content>
	<Sidebar.Footer class="border-t border-sidebar-border">
		<NavMain groups={nav.footer} class="p-0" />
		<NavUser user={userData} />
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
