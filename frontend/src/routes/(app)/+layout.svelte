<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { onMount, onDestroy } from 'svelte';
	import AppSidebar from '$lib/components/layout/app-sidebar.svelte';
	import TopBar from '$lib/components/layout/top-bar.svelte';
	import NotificationToasts from '$lib/components/notifications/notification-toasts.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import CreateFirstProjectModal from '@/components/modals/create-first-project-modal.svelte';
	import { page } from '$app/stores';
	import { getRouteLabel } from '$lib/config/routes';

	let { children } = $props();

	let sidebarOpen = $state(true);


	onMount(() => {
		const saved = document.cookie
			.split('; ')
			.find(c => c.startsWith('sidebar:state='))
			?.split('=')[1];
		if (saved !== undefined) {
			sidebarOpen = saved === 'true';
		}
	});

	$effect(() => {
		if (!auth.isLoading && !auth.isAuthenticated) {
			goto('/login');
		}
	});

	$effect(() => {
		if (auth.isAuthenticated) {
			projectsStore.fetchProjects();
		}
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			if (!notificationStore.hasLoaded && !notificationStore.isLoading) {
				notificationStore.loadNotifications();
			}

			if (!notificationStore.isConnected && notificationStore.hasLoaded) {
				notificationStore.connectSSE();
				console.log('[Notifications] SSE connected');
			}
		}
	});

	onDestroy(() => {
		notificationStore.disconnectSSE();
		console.log('[Notifications] SSE disconnected');
	});

	let showRequiredProjectCreateModal = $derived(
		auth.isAuthenticated &&
			!auth.isLoading &&
			!projectsStore.isLoading &&
			projectsStore.hasFetched &&
			projectsStore.projects.length === 0
	);

	let breadcrumbs = $derived.by(() => {
		const path = $page.url.pathname;
		const segments = path.split('/').filter(Boolean);

		return segments.map((segment, index) => ({
			label: getRouteLabel(segment),
			href: '/' + segments.slice(0, index + 1).join('/')
		}));
	});
</script>

<NotificationToasts />
<CreateFirstProjectModal open={showRequiredProjectCreateModal} />

{#if auth.isLoading}
	<div class="min-h-screen flex items-center justify-center">
		<Spinner />
		<p class="text-muted-foreground">Loading...</p>
	</div>
{:else if auth.isAuthenticated}
	<Sidebar.Provider open={sidebarOpen}>
		<AppSidebar variant="inset" />
		<Sidebar.Inset>
			<div class="flex flex-1 flex-col">
				<div class="flex flex-1 flex-col rounded-lg bg-background shadow-sm overflow-hidden">
					<TopBar {breadcrumbs} />
					<main class="flex-1 overflow-auto p-6" style="scrollbar-gutter: stable;">
						{@render children()}
					</main>
				</div>
			</div>
		</Sidebar.Inset>
	</Sidebar.Provider>
{/if}

<style>
	:global([data-variant="inset"][data-state="collapsed"] [data-slot="sidebar-gap"]) {
		width: var(--sidebar-width-icon) !important;
	}
	:global([data-variant="inset"][data-state="collapsed"] [data-slot="sidebar-container"]) {
		width: var(--sidebar-width-icon) !important;
		overflow: visible !important;
		padding: 0 !important;
	}
</style>
