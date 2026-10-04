<script lang="ts">
	import { afterNavigate, goto, onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { auth } from '$lib/stores/auth.svelte';
	import { onboardingStore } from '$lib/stores/onboarding.svelte';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { onMount, untrack } from 'svelte';
	import AppSidebar from '$lib/components/layout/app-sidebar.svelte';
	import TopBar from '$lib/components/layout/top-bar.svelte';
	import NotificationToasts from '$lib/components/notifications/notification-toasts.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { SIDEBAR_COOKIE_NAME } from '$lib/components/ui/sidebar/constants.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import CreateFirstProjectModal from '$lib/components/modals/create-first-project-modal.svelte';
	import { crumbHref, getRouteLabel, PROJECT_PARAM, ROUTES, UUID_REGEX } from '$lib/config/routes';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import ActivityPanel from '$lib/components/activity/activity-panel.svelte';

	let { children } = $props();

	let sidebarOpen = $state(true);

	onMount(() => {
		const saved = document.cookie
			.split('; ')
			.find((c) => c.startsWith(`${SIDEBAR_COOKIE_NAME}=`))
			?.split('=')[1];
		if (saved !== undefined) {
			sidebarOpen = saved === 'true';
		}
	});

	$effect(() => {
		if (!auth.isLoading && !auth.isAuthenticated) {
			goto(ROUTES.loginThen(page.url.pathname + page.url.search));
		}
	});

	$effect(() => {
		if (auth.isAuthenticated) {
			untrack(() => projectsStore.fetchProjects());
		}
	});

	function projectNamedBy(url: URL | undefined) {
		const slug = url?.searchParams.get(PROJECT_PARAM);
		if (!slug || slug === projectsStore.activeProject?.slug) return null;
		return projectsStore.projects.find((p) => p.slug === slug) ?? null;
	}

	function settleProjectParam() {
		if (!page.url.searchParams.has(PROJECT_PARAM)) return;
		if (!projectsStore.hasFetched && !projectsStore.error) return;
		const project = projectNamedBy(page.url);
		if (project) projectsStore.setActiveProject(project);
		const url = new URL(location.href);
		url.searchParams.delete(PROJECT_PARAM);
		void goto(url, { replaceState: true, keepFocus: true, noScroll: true });
	}

	onNavigate((navigation) => {
		const project = projectNamedBy(navigation.to?.url);
		if (project) projectsStore.setActiveProject(project);
	});

	afterNavigate(() => settleProjectParam());

	$effect(() => {
		if (projectsStore.hasFetched || projectsStore.error) untrack(settleProjectParam);
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading && !capabilitiesStore.hasFetched) {
			capabilitiesStore.fetch();
		}
	});

	$effect(() => {
		if (auth.isAuthenticated && !auth.isLoading) {
			if (!onboardingStore.hasFetched) {
				untrack(() => onboardingStore.fetchStatus());
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
		const projectId = projectsStore.activeProject?.id;
		if (!auth.isAuthenticated || auth.isLoading || !projectId) return;
		untrack(() => {
			if (notificationStore.isLoading && notificationStore.projectId === projectId) return;
			if (notificationStore.hasLoaded && notificationStore.projectId === projectId) return;
			notificationStore.loadNotifications(projectId);
		});
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

	let showRequiredProjectCreateModal = $derived(
		auth.isAuthenticated &&
			!auth.isLoading &&
			onboardingStore.status?.completed === true &&
			!projectsStore.isLoading &&
			projectsStore.hasFetched &&
			projectsStore.projects.length === 0
	);

	const NEW_ENTITY_LABEL: Record<string, string> = {
		contexts: 'New context',
		engines: 'New engine'
	};

	let breadcrumbs = $derived.by(() => {
		const path = page.url.pathname;
		const segments = path.split('/').filter(Boolean);

		return segments
			.flatMap((segment, index) => {
				const href = crumbHref('/' + segments.slice(0, index + 1).join('/'));
				const trail = breadcrumbStore.getTrail(segment);
				if (trail) return trail;
				const override = breadcrumbStore.getLabel(segment);
				if (override) return { label: override, href };

				if (segment === 'new') {
					const parent = segments[index - 1];
					return { label: NEW_ENTITY_LABEL[parent] ?? 'New', href };
				}

				if (UUID_REGEX.test(segment)) {
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
		<a
			href="#content"
			class="sr-only rounded-md bg-background text-sm font-medium shadow-md ring-2 ring-ring focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-60 focus:px-3 focus:py-2"
			onclick={(e) => {
				e.preventDefault();
				document.getElementById('content')?.focus();
			}}
		>
			Skip to content
		</a>
		<AppSidebar variant="inset" />
		<Sidebar.Inset class="min-w-0">
			<div class="flex flex-1 flex-col min-h-0 overflow-hidden">
				<div
					class="relative flex flex-1 flex-col rounded-lg bg-background shadow-sm overflow-hidden"
				>
					<TopBar {breadcrumbs} />
					<div class="relative flex flex-1 min-h-0 overflow-hidden">
						<ScrollArea class="min-h-0 min-w-0 flex-1">
							<div
								id="content"
								tabindex="-1"
								class="p-6 outline-none has-[[data-selection-bar]]:pb-48 sm:has-[[data-selection-bar]]:pb-32"
							>
								{@render children()}
							</div>
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
