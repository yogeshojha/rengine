<script lang="ts">
	import { page } from '$app/stores';
	import * as Breadcrumb from '$lib/components/ui/breadcrumb/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import Bell from 'lucide-svelte/icons/bell';
	import { projectsStore } from '$lib/stores/projects.svelte';

	// Generate breadcrumbs from current path
	function getBreadcrumbs() {
		const pathname = $page.url.pathname;
		const segments = pathname.split('/').filter(Boolean);

		return segments.map((segment, index) => {
			const href = '/' + segments.slice(0, index + 1).join('/');
			const label = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');
			return { href, label };
		});
	}

	// Mock notifications - replace with real data
	const notifications = [
		{ id: 1, title: 'Scan completed', description: 'Target scan finished', time: '2m ago' },
		{ id: 2, title: 'New vulnerability', description: 'Critical CVE found', time: '1h ago' }
	];
</script>

<header
	class="flex h-16 shrink-0 items-center justify-between gap-2 border-b px-4 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12"
>
	<div class="flex items-center gap-2">
		<Sidebar.Trigger class="-ms-1" />
		<Separator orientation="vertical" class="me-2 h-4" />

		<!-- Project indicator -->
		{#if projectsStore.activeProject}
			<span class="text-sm text-muted-foreground">
				{projectsStore.activeProject.name}
			</span>
			<Separator orientation="vertical" class="mx-2 h-4" />
		{/if}

		<!-- Breadcrumbs -->
		<Breadcrumb.Root>
			<Breadcrumb.List>
				{#each getBreadcrumbs() as crumb, index}
					{#if index > 0}
						<Breadcrumb.Separator class="hidden md:block" />
					{/if}
					<Breadcrumb.Item class="hidden md:block">
						{#if index === getBreadcrumbs().length - 1}
							<Breadcrumb.Page>{crumb.label}</Breadcrumb.Page>
						{:else}
							<Breadcrumb.Link href={crumb.href}>{crumb.label}</Breadcrumb.Link>
						{/if}
					</Breadcrumb.Item>
				{/each}
			</Breadcrumb.List>
		</Breadcrumb.Root>
	</div>

	<!-- Right side - Notifications -->
	<div class="flex items-center gap-2">
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button variant="ghost" size="icon" class="relative" {...props}>
						<Bell class="size-4" />
						{#if notifications.length > 0}
							<span
								class="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] text-destructive-foreground"
							>
								{notifications.length}
							</span>
						{/if}
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content class="w-80" align="end">
				<DropdownMenu.Label>Notifications</DropdownMenu.Label>
				<DropdownMenu.Separator />
				{#each notifications as notification (notification.id)}
					<DropdownMenu.Item class="flex flex-col items-start gap-1 p-3">
						<div class="flex w-full justify-between">
							<span class="font-medium">{notification.title}</span>
							<span class="text-xs text-muted-foreground">{notification.time}</span>
						</div>
						<span class="text-sm text-muted-foreground">{notification.description}</span>
					</DropdownMenu.Item>
				{/each}
				{#if notifications.length === 0}
					<div class="p-4 text-center text-sm text-muted-foreground">No new notifications</div>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</header>