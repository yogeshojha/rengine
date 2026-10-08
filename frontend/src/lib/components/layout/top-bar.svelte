<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import Activity from '@lucide/svelte/icons/activity';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import ActivityGlance from '$lib/components/activity/activity-glance.svelte';
	import { activityFeed } from '$lib/stores/activity-feed.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import CommandSearch from '$lib/components/layout/command-search.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import NotificationsMenu from '$lib/components/layout/notifications-menu.svelte';
	import QuickActionsMenu from '$lib/components/layout/quick-actions-menu.svelte';
	import ToolboxMenu from '$lib/components/toolbox/toolbox-menu.svelte';
	import ToolboxDialog from '$lib/components/toolbox/toolbox-dialog.svelte';
	import { toolbox } from '$lib/stores/toolbox.svelte';
	import { safeHref } from '$lib/utilities/links';

	interface BreadcrumbItem {
		label: string;
		href?: string;
		/** The page has not named this segment yet. */
		pending?: boolean;
	}

	let { breadcrumbs = [] }: { breadcrumbs?: BreadcrumbItem[] } = $props();

	let addTargetOpen = $state(false);
	const handleAddTarget = () => (addTargetOpen = true);
	let launchOpen = $state(false);
	let scanValue = $state<string | undefined>(undefined);
	const handleScan = (value?: string) => {
		scanValue = value;
		launchOpen = true;
	};

	const handleToolbox = (value: string) => toolbox.open({ value });
</script>

<header
	class="@container/topbar sticky top-0 z-50 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4"
>
	<Sidebar.Trigger class="-ms-1" />
	<Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />

	{#if breadcrumbs.length > 0}
		<Breadcrumb.Root class="min-w-0">
			<Breadcrumb.List class="flex-nowrap gap-1.5 whitespace-nowrap sm:gap-1.5">
				{#each breadcrumbs as crumb, i (`${i}:${crumb.href ?? crumb.label}`)}
					{@const last = i === breadcrumbs.length - 1}
					{#if i > 0}
						<Breadcrumb.Separator class="hidden @3xl/topbar:block" />
					{/if}
					<Breadcrumb.Item class={last ? 'min-w-0' : 'hidden shrink-0 @3xl/topbar:inline-flex'}>
						{#if crumb.pending}
							<Skeleton class="h-4 w-20" aria-hidden="true" />
							<span class="sr-only">{crumb.label}</span>
						{:else if last}
							<Breadcrumb.Page class="truncate font-medium" title={crumb.label}>
								{crumb.label}
							</Breadcrumb.Page>
						{:else if crumb.href}
							<Breadcrumb.Link
								href={safeHref(crumb.href)}
								class="max-w-48 truncate"
								title={crumb.label}
							>
								{crumb.label}
							</Breadcrumb.Link>
						{:else}
							<span class="max-w-48 truncate" title={crumb.label}>{crumb.label}</span>
						{/if}
					</Breadcrumb.Item>
				{/each}
			</Breadcrumb.List>
		</Breadcrumb.Root>
	{/if}

	<div class="ml-3 hidden @5xl/topbar:block">
		<ActivityGlance />
	</div>

	<div class="flex-1"></div>

	<CommandSearch onAddTarget={handleAddTarget} onScan={handleScan} onToolbox={handleToolbox} />
	<ToolboxMenu bind:open={toolbox.dialogOpen} />
	<Hint text="Activity">
		{#snippet child(props)}
			<Button
				{...props}
				variant="ghost"
				size="icon"
				class="relative @5xl/topbar:hidden"
				aria-label="Activity"
				aria-expanded={activityFeed.open}
				data-activity-glance
				onclick={() => activityFeed.toggle()}
			>
				{#if liveScans.hasLive}
					<Spinner class="size-4 text-info" />
				{:else}
					<Activity class="size-4" />
				{/if}
				{#if activityFeed.failure && !liveScans.hasLive}
					<span class="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-destructive"></span>
				{/if}
			</Button>
		{/snippet}
	</Hint>
	<NotificationsMenu />
	<QuickActionsMenu onAddTarget={handleAddTarget} />
</header>

<AddTargetModal bind:open={addTargetOpen} />
<LaunchDialog
	bind:open={launchOpen}
	targetValues={scanValue ? [scanValue] : undefined}
	onClose={() => (scanValue = undefined)}
/>
<ToolboxDialog bind:open={toolbox.dialogOpen} bind:launch={toolbox.launch} />
