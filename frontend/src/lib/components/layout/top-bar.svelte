<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { setMode, resetMode } from 'mode-watcher';
	import SearchIcon from '@lucide/svelte/icons/search';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import BuildingIcon from '@lucide/svelte/icons/building';
	import CogIcon from '@lucide/svelte/icons/cog';
	import LayersIcon from '@lucide/svelte/icons/layers';
	import BellIcon from '@lucide/svelte/icons/bell';
	import SunIcon from '@lucide/svelte/icons/sun';
	import MoonIcon from '@lucide/svelte/icons/moon';
	import MonitorIcon from '@lucide/svelte/icons/monitor';
	import ShieldAlertIcon from '@lucide/svelte/icons/shield-alert';
	import CheckCircleIcon from '@lucide/svelte/icons/check-circle';
	import AlertTriangleIcon from '@lucide/svelte/icons/alert-triangle';
	import InfoIcon from '@lucide/svelte/icons/info';

	let commandOpen = $state(false);

	// we will get this through api later
	const notifications = $state([
		{
			id: 1,
			type: 'critical',
			title: 'Critical Vulnerability Found',
			message: 'SQL Injection detected on api.example.com',
			time: '2 minutes ago',
			read: false
		},
		{
			id: 2,
			type: 'warning',
			title: 'Scan Completed with Warnings',
			message: 'Target scan finished with 3 warnings',
			time: '15 minutes ago',
			read: false
		},
		{
			id: 3,
			type: 'success',
			title: 'Scan Completed',
			message: 'Full reconnaissance scan completed for acme.com',
			time: '1 hour ago',
			read: true
		},
		{
			id: 4,
			type: 'info',
			title: 'New Asset Discovered',
			message: '5 new subdomains found for example.org',
			time: '3 hours ago',
			read: true
		}
	]);

	const unreadCount = $derived(notifications.filter((n) => !n.read).length);

	const getNotificationIcon = (type: string) => {
		switch (type) {
			case 'critical':
				return { icon: ShieldAlertIcon, class: 'text-red-500' };
			case 'warning':
				return { icon: AlertTriangleIcon, class: 'text-yellow-500' };
			case 'success':
				return { icon: CheckCircleIcon, class: 'text-green-500' };
			default:
				return { icon: InfoIcon, class: 'text-blue-500' };
		}
	};

	$effect(() => {
		const handleKeydown = (e: KeyboardEvent) => {
			if (e.ctrlKey && e.shiftKey && e.key === 'S') {
				e.preventDefault();
				commandOpen = !commandOpen;
			}
		};

		document.addEventListener('keydown', handleKeydown);
		return () => document.removeEventListener('keydown', handleKeydown);
	});

	const handleAddTarget = () => {
		console.log('Add Target clicked');
		// TODO: Open Add Target modal
	};

	const handleAddOrganization = () => {
		console.log('Add Organization clicked');
		// TODO: Open Add Organization modal
	};

	const handleNewScanEngine = () => {
		console.log('New Scan Engine clicked');
		// TODO: Navigate to scan engine creation
	};

	const handleNewScanContext = () => {
		console.log('New Scan Context clicked');
		// TODO: Navigate to scan context creation
	};

	const markAllAsRead = () => {
		notifications.forEach((n) => (n.read = true));
	};
</script>

<header
	class="sticky top-0 z-50 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4"
>
	<Sidebar.Trigger class="-ml-1" />
	<Separator orientation="vertical" class="mr-2 h-4" />

	<!-- TODO: Remove this placeholder once breadcrumbs or page title is added -->
	<div class="flex-1"></div>

	<Button
		variant="outline"
		class="relative h-9 w-full justify-start rounded-md text-sm text-muted-foreground sm:w-64 md:w-80"
		onclick={() => (commandOpen = true)}
	>
		<SearchIcon class="mr-2 h-4 w-4" />
		<span class="hidden lg:inline-flex">Search...</span>
		<span class="inline-flex lg:hidden">Search...</span>
		<kbd
			class="pointer-events-none absolute right-1.5 top-1.5 hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex"
		>
			Ctrl+Shift+S
		</kbd>
	</Button>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon" class="relative">
					<BellIcon class="h-4 w-4" />
					{#if unreadCount > 0}
						<Badge
							class="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-[10px] bg-red-500 text-white"
						>
							{unreadCount}
						</Badge>
					{/if}
					<span class="sr-only">Notifications</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-80">
			<div class="flex items-center justify-between px-3 py-2">
				<DropdownMenu.Label class="p-0">Notifications</DropdownMenu.Label>
				{#if unreadCount > 0}
					<Button variant="ghost" size="sm" class="h-auto p-0 text-xs" onclick={markAllAsRead}>
						Mark all as read
					</Button>
				{/if}
			</div>
			<DropdownMenu.Separator />
			<div class="h-80 overflow-y-auto thin-scrollbar">
				{#each notifications as notification (notification.id)}
					{@const iconData = getNotificationIcon(notification.type)}
					<DropdownMenu.Item
						class="flex items-start gap-3 p-3 cursor-pointer my-1 {!notification.read
							? 'bg-muted/50'
							: ''}"
					>
						<div class="mt-0.5">
							<iconData.icon class="h-4 w-4 {iconData.class}" />
						</div>
						<div class="flex-1 space-y-1">
							<p class="text-sm font-medium leading-none">{notification.title}</p>
							<p class="text-xs text-muted-foreground">{notification.message}</p>
							<p class="text-xs text-muted-foreground">{notification.time}</p>
						</div>
						{#if !notification.read}
							<div class="h-2 w-2 rounded-full bg-blue-500"></div>
						{/if}
					</DropdownMenu.Item>
				{/each}
			</div>
			<DropdownMenu.Separator />
			<DropdownMenu.Item class="justify-center text-center">
				View all notifications
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon">
					<PlusIcon class="h-4 w-4" />
					<span class="sr-only">Quick Actions</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-56">
			<DropdownMenu.Label>Create New</DropdownMenu.Label>
			<DropdownMenu.Separator />
			<DropdownMenu.Item onclick={handleAddTarget}>
				<CrosshairIcon class="mr-2 h-4 w-4" />
				Add Target
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={handleAddOrganization}>
				<BuildingIcon class="mr-2 h-4 w-4" />
				Add Organization
			</DropdownMenu.Item>
			<DropdownMenu.Separator />
			<DropdownMenu.Label class="text-xs text-muted-foreground">Automation</DropdownMenu.Label>
			<DropdownMenu.Item onclick={handleNewScanEngine}>
				<CogIcon class="mr-2 h-4 w-4" />
				New Scan Engine
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={handleNewScanContext}>
				<LayersIcon class="mr-2 h-4 w-4" />
				New Scan Context
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon">
					<SunIcon
						class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90"
					/>
					<MoonIcon
						class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0"
					/>
					<span class="sr-only">Toggle theme</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end">
			<DropdownMenu.Item onclick={() => setMode('light')}>
				<SunIcon class="mr-2 h-4 w-4" />
				Light
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => setMode('dark')}>
				<MoonIcon class="mr-2 h-4 w-4" />
				Dark
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => resetMode()}>
				<MonitorIcon class="mr-2 h-4 w-4" />
				System
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
</header>

<Dialog.Root bind:open={commandOpen}>
	<Dialog.Content class="overflow-hidden p-0 shadow-lg sm:max-w-[550px]">
		<Command.Root class="[&_[data-cmd-input-wrapper]]:border-b">
			<Command.Input placeholder="Search targets, vulnerabilities, assets..." />
			<Command.List>
				<Command.Empty>No results found.</Command.Empty>

				<Command.Group heading="Quick Actions">
					<Command.Item
						onSelect={() => {
							commandOpen = false;
							handleAddTarget();
						}}
					>
						<CrosshairIcon class="mr-2 h-4 w-4" />
						<span>Add Target</span>
					</Command.Item>
					<Command.Item
						onSelect={() => {
							commandOpen = false;
							handleAddOrganization();
						}}
					>
						<BuildingIcon class="mr-2 h-4 w-4" />
						<span>Add Organization</span>
					</Command.Item>
					<Command.Item
						onSelect={() => {
							commandOpen = false;
							handleNewScanEngine();
						}}
					>
						<CogIcon class="mr-2 h-4 w-4" />
						<span>New Scan Engine</span>
					</Command.Item>
					<Command.Item
						onSelect={() => {
							commandOpen = false;
							handleNewScanContext();
						}}
					>
						<LayersIcon class="mr-2 h-4 w-4" />
						<span>New Scan Context</span>
					</Command.Item>
				</Command.Group>
			</Command.List>
		</Command.Root>
	</Dialog.Content>
</Dialog.Root>

<!-- thinbar scrollbar -->
<style>
    /* Firefox */
    .thin-scrollbar {
        scrollbar-width: thin;
        scrollbar-color: hsl(var(--muted-foreground) / 0.3) transparent;
    }

    /* Chrome, Safari, Edge */
    .thin-scrollbar::-webkit-scrollbar {
        width: 1px;
    }

    .thin-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }

    .thin-scrollbar::-webkit-scrollbar-thumb {
        background-color: hsl(var(--muted-foreground) / 0.3);
        border-radius: 1px;
    }
</style>
