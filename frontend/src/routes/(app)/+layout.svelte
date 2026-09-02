<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte';
	import { onboardingStore } from '$lib/stores/onboarding.svelte';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { onMount } from 'svelte';
	import AppSidebar from '$lib/components/layout/app-sidebar.svelte';
	import TopBar from '$lib/components/layout/top-bar.svelte';
	import NotificationToasts from '$lib/components/notifications/notification-toasts.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import CreateFirstProjectModal from '@/components/modals/create-first-project-modal.svelte';
	import { getRouteLabel, ROUTES } from '$lib/config/routes';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import ActivityPanel from '$lib/components/activity/activity-panel.svelte';

	let { children } = $props();

	let sidebarOpen = $state(true);

	onMount(() => {
		const saved = document.cookie
			.split('; ')
			.find((c) => c.startsWith('sidebar:state='))
			?.split('=')[1];
		if (saved !== undefined) {
			sidebarOpen = saved === 'true';
		}
	});

	$effect(() => {
		if (!auth.isLoading && !auth.isAuthenticated) {
			goto(ROUTES.login);
		}
	});

	$effect(() => {
		if (auth.isAuthenticated) {
			projectsStore.fetchProjects();
		}
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading && !capabilitiesStore.hasFetched) {
			capabilitiesStore.fetch();
		}
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			if (!onboardingStore.hasFetched) {
				onboardingStore.fetchStatus();
				return;
			}
			const status = onboardingStore.status;
			if (
				status &&
				!status.completed &&
				status.can_setup &&
				page.url.pathname !== ROUTES.onboarding
			) {
				goto(ROUTES.onboarding);
			}
		}
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			if (!notificationStore.hasLoaded && !notificationStore.isLoading) {
				notificationStore.loadNotifications();
			}
		}
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			const projectId = projectsStore.activeProject?.id;
			sseStore.init(projectId);
			notificationStore.subscribeSSE();

			return () => {
				notificationStore.unsubscribeSSE();
				sseStore.destroy();
			};
		}
	});

	$effect(() => {
		const projectId = projectsStore.activeProject?.id;
		if (auth.isAuthenticated && !auth.isLoading && projectId) liveScans.init(projectId);
	});

	let prevProjectId: string | undefined;
	$effect(() => {
		const projectId = projectsStore.activeProject?.id;
		if (sseStore.isConnected && projectId && projectId !== prevProjectId) {
			if (prevProjectId) {
				sseStore.switchProject(prevProjectId, projectId);
			}
			prevProjectId = projectId;
		}
	});

	let showRequiredProjectCreateModal = $derived(
		auth.isAuthenticated &&
			!auth.isLoading &&
			onboardingStore.status?.completed === true &&
			!projectsStore.isLoading &&
			projectsStore.hasFetched &&
			projectsStore.projects.length === 0
	);

	const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

	const NEW_ENTITY_LABEL: Record<string, string> = {
		contexts: 'New context',
		engines: 'New engine',
		targets: 'New target',
		scans: 'New scan'
	};

	let breadcrumbs = $derived.by(() => {
		const path = page.url.pathname;
		const segments = path.split('/').filter(Boolean);

		return segments
			.map((segment, index) => {
				const href = '/' + segments.slice(0, index + 1).join('/');
				const override = breadcrumbStore.getLabel(segment);
				if (override) return { label: override, href };

				if (segment === 'new') {
					const parent = segments[index - 1];
					return { label: NEW_ENTITY_LABEL[parent] ?? 'New', href };
				}

				if (UUID_RE.test(segment)) {
					return { label: segment.slice(0, 8), href };
				}

				const label = getRouteLabel(segment);
				if (!label) return null;
				return { label, href };
			})
			.filter(Boolean) as { label: string; href: string }[];
	});
</script>

<NotificationToasts />
<CreateFirstProjectModal open={showRequiredProjectCreateModal} />

{#if auth.isLoading}
	<div class="min-h-screen flex flex-col items-center justify-center gap-3">
		<Spinner />
		<p class="text-muted-foreground">Loading…</p>
	</div>
{:else if auth.isAuthenticated}
	<Sidebar.Provider open={sidebarOpen} class="!h-svh !min-h-0 overflow-hidden">
		<AppSidebar variant="inset" />
		<Sidebar.Inset class="min-w-0">
			<div class="flex flex-1 flex-col min-h-0 overflow-hidden">
				<div
					class="relative flex flex-1 flex-col rounded-lg bg-background shadow-sm overflow-hidden"
				>
					<TopBar {breadcrumbs} />
					<div class="relative flex flex-1 min-h-0 overflow-hidden">
						<ScrollArea class="min-h-0 min-w-0 flex-1">
							<main class="p-6">
								{@render children()}
							</main>
						</ScrollArea>
						<ActivityPanel />
					</div>
				</div>
			</div>
		</Sidebar.Inset>
	</Sidebar.Provider>
{/if}

<style>
	:global([data-variant='inset'][data-state='collapsed'] [data-slot='sidebar-gap']) {
		width: var(--sidebar-width-icon) !important;
	}
	:global([data-variant='inset'][data-state='collapsed'] [data-slot='sidebar-container']) {
		width: var(--sidebar-width-icon) !important;
		overflow: visible !important;
		padding: 0 !important;
	}
</style>
