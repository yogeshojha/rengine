<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ActivityGlance from '$lib/components/activity/activity-glance.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import CommandSearch from '$lib/components/layout/command-search.svelte';
	import NotificationsMenu from '$lib/components/layout/notifications-menu.svelte';
	import QuickActionsMenu from '$lib/components/layout/quick-actions-menu.svelte';
	import ThemeToggle from '$lib/components/layout/theme-toggle.svelte';

	interface BreadcrumbItem {
		label: string;
		href?: string;
	}

	let { breadcrumbs = [] }: { breadcrumbs?: BreadcrumbItem[] } = $props();

	let addTargetOpen = $state(false);
	const handleAddTarget = () => (addTargetOpen = true);
</script>

<header class="sticky top-0 z-50 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
	<Sidebar.Trigger class="-ms-1" />
	<Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />

	{#if breadcrumbs.length > 0}
		<nav class="flex items-center gap-1.5 text-sm">
			{#each breadcrumbs as crumb, i (crumb.href ?? crumb.label)}
				{#if i > 0}
					<ChevronRight class="size-3.5 text-muted-foreground/50" />
				{/if}

				{#if crumb.href && i < breadcrumbs.length - 1}
					<a
						href={crumb.href}
						class="text-muted-foreground hover:text-foreground transition-colors"
					>
						{crumb.label}
					</a>
				{:else}
					<span class="text-foreground font-medium">{crumb.label}</span>
				{/if}
			{/each}
		</nav>
	{/if}

	<div class="ml-3 hidden md:block">
		<ActivityGlance />
	</div>

	<div class="flex-1"></div>

	<CommandSearch onAddTarget={handleAddTarget} />
	<NotificationsMenu />
	<QuickActionsMenu onAddTarget={handleAddTarget} />
	<ThemeToggle />
</header>

<AddTargetModal bind:open={addTargetOpen} />
