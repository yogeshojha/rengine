<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Activity from '@lucide/svelte/icons/activity';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import ActivityGlance from '$lib/components/activity/activity-glance.svelte';
	import { activityFeed } from '$lib/stores/activity-feed.svelte';
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
		<nav
			aria-label="Breadcrumb"
			class="flex min-w-0 items-center gap-1.5 text-sm whitespace-nowrap"
		>
			{#each breadcrumbs as crumb, i (`${i}:${crumb.href ?? crumb.label}`)}
				{@const last = i === breadcrumbs.length - 1}
				{#if i > 0}
					<ChevronRight
						class="hidden size-3.5 shrink-0 text-muted-foreground/50 @3xl/topbar:block"
					/>
				{/if}

				{#if crumb.href && !last}
					<a
						href={safeHref(crumb.href)}
						class="hidden max-w-48 min-w-0 truncate text-muted-foreground transition-colors hover:text-foreground @3xl/topbar:inline"
					>
						{crumb.label}
					</a>
				{:else}
					<span
						aria-current={last ? 'page' : undefined}
						class={[
							'font-medium text-foreground',
							last ? 'truncate' : 'hidden max-w-48 min-w-0 truncate @3xl/topbar:inline'
						]}>{crumb.label}</span
					>
				{/if}
			{/each}
		</nav>
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
				class="@5xl/topbar:hidden"
				aria-label="Activity"
				aria-expanded={activityFeed.open}
				data-activity-glance
				onclick={() => activityFeed.toggle()}
			>
				<Activity class="size-4" />
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
