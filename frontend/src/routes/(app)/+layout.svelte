<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import AppSidebar from '$lib/components/layout/app-sidebar.svelte';
	import TopBar from '$lib/components/layout/top-bar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import CreateFirstProjectModal from '@/components/modals/create-first-project-modal.svelte';

	let { children } = $props();

	// Redirect to login if not authenticated
	$effect(() => {
		if (!auth.isLoading && !auth.isAuthenticated) {
			goto('/login');
		}
	});

	// authenticated
	$effect(() => {
		if (auth.isAuthenticated) {
			projectsStore.fetchProjects();
		}
	});


	let showRequiredProjectCreateModal = $derived(
		auth.isAuthenticated &&
		!auth.isLoading &&
		!projectsStore.isLoading &&
		projectsStore.hasFetched &&
		projectsStore.projects.length === 0
	);
</script>

<CreateFirstProjectModal open={showRequiredProjectCreateModal} />

{#if auth.isLoading}
	<div class="min-h-screen flex items-center justify-center">
		<Spinner />
		<p class="text-muted-foreground">Loading...</p>
	</div>
{:else if auth.isAuthenticated}
	<Sidebar.Provider>
		<AppSidebar />
		<Sidebar.Inset>
			<TopBar />
			<main class="flex-1 overflow-auto">
				{@render children()}
			</main>
		</Sidebar.Inset>
	</Sidebar.Provider>
{/if}
