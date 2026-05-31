<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Sheet from '$lib/components/ui/sheet/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { setMode, resetMode } from 'mode-watcher';
	import {
		Search,
		Plus,
		Crosshair,
		Building,
		Cog,
		Layers,
		Bell,
		Sun,
		Moon,
		Monitor,
		ShieldAlert,
		CircleCheck,
		TriangleAlert,
		Info,
		Activity,
		ChevronRight,
		Trash,
		Trash2,
		ExternalLink,
		Scan,
		Server,
		Shield,
		Bug,
		Target,
		HardDrive,
		Plug,
		SearchIcon
	} from 'lucide-svelte';
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { relativeTime } from '$lib/utilities/dates.js';
	import type { NotificationType, NotificationSeverity } from '$lib/types/notification';
	import { toast } from 'svelte-sonner';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import ActivityGlance from '$lib/components/activity/activity-glance.svelte';

	let commandOpen = $state(false);
	let scansSheetOpen = $state(false);
	let notificationsModalOpen = $state(false);
	let notificationsDropdownOpen = $state(false);
	let selectedFilter = $state<NotificationType | 'all'>('all');
	let addTargetOpen = $state(false);

	const getSeverityIcon = (severity: NotificationSeverity) => {
		switch (severity) {
			case 'error':
				return { icon: ShieldAlert, class: 'text-red-500' };
			case 'warning':
				return { icon: TriangleAlert, class: 'text-yellow-500' };
			case 'success':
				return { icon: CircleCheck, class: 'text-green-500' };
			default:
				return { icon: Info, class: 'text-blue-500' };
		}
	};

	const getTypeIcon = (type: NotificationType) => {
		switch (type) {
			case 'scan':
				return Scan;
			case 'system':
				return Server;
			case 'security':
				return Shield;
			case 'vulnerability':
				return Bug;
			case 'target':
				return Target;
			case 'resource':
				return HardDrive;
			case 'integration':
				return Plug;
		}
	};

	const filteredNotifications = $derived(
		selectedFilter === 'all'
			? notificationStore.notifications
			: notificationStore.notifications.filter((n) => n.type === selectedFilter)
	);

	const typeCounts = $derived.by(() => {
		const counts: Record<NotificationType | 'all', number> = {
			all: notificationStore.notifications.length,
			scan: 0,
			system: 0,
			security: 0,
			vulnerability: 0,
			target: 0,
			resource: 0,
			integration: 0
		};

		notificationStore.notifications.forEach((n) => {
			counts[n.type]++;
		});

		return counts;
	});

	const handleNotificationClick = (notificationId: number) => {
		const notification = notificationStore.notifications.find((n) => n.id === notificationId);
		if (!notification) return;

		notificationStore.markAsRead(notificationId);

		const metadata = notification.notification_metadata;
		if (metadata?.url) {
			if (metadata.open_new_tab) {
				window.open(metadata.url, '_blank', 'noopener,noreferrer');
			} else {
				window.location.href = metadata.url;
			}
		}
	};

	const handleActionClick = (notificationId: number, event: Event) => {
		event.stopPropagation();

		const notification = notificationStore.notifications.find((n) => n.id === notificationId);
		if (!notification) return;

		notificationStore.markAsRead(notificationId);

		const metadata = notification.notification_metadata;
		if (metadata?.url) {
			if (metadata.open_new_tab) {
				window.open(metadata.url, '_blank', 'noopener,noreferrer');
			} else {
				window.location.href = metadata.url;
			}
		}
	};

	const handleDeleteNotification = async (id: number, event: Event) => {
		event.stopPropagation();
		try {
			await notificationStore.deleteNotification(id);
		} catch (error) {
			console.error('Failed to delete notification:', error);
		}
	};

	const handleMarkAllAsRead = async () => {
		try {
			await notificationStore.markAllAsRead();
		} catch (error) {
			console.error('Failed to mark all as read:', error);
		}
	};

	const handleClearAll = async () => {
		try {
			await notificationStore.clearAll();
		} catch (error) {
			console.error('Failed to clear all notifications:', error);
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
		addTargetOpen = true;
	};

	const handleAddOrganization = () => {
		toast.info('Coming soon', {
			description: 'Add Organization will be available in a future update.'
		});
	};

	const handleNewScanEngine = () => {
		toast.info('Coming soon', {
			description: 'Scan Engine configuration will be available in a future update.'
		});
	};

	const handleNewScanContext = () => {
		toast.info('Coming soon', {
			description: 'Scan Context configuration will be available in a future update.'
		});
	};

	interface BreadcrumbItem {
		label: string;
		href?: string;
	}

	let { breadcrumbs = [] }: { breadcrumbs?: BreadcrumbItem[] } = $props();
</script>

<header class="sticky top-0 z-50 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
	<Sidebar.Trigger class="-ms-1" />
	<Separator orientation="vertical" class="mx-2 data-[orientation=vertical]:h-4" />

	<!-- Breadcrumbs -->
	{#if breadcrumbs.length > 0}
		<nav class="flex items-center gap-1.5 text-sm">
			{#each breadcrumbs as crumb, i}
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

	<!-- Notifications Dropdown -->
	<DropdownMenu.Root bind:open={notificationsDropdownOpen}>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon" class="relative">
					<Bell class="h-4 w-4" />
					{#if notificationStore.unreadCount > 0}
						<Badge
							class="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-[10px] bg-red-500 text-white"
						>
							{notificationStore.unreadCount}
						</Badge>
					{/if}
					<span class="sr-only">Notifications</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-80">
			<div class="flex items-center justify-between px-3 py-2">
				<DropdownMenu.Label class="p-0">Notifications</DropdownMenu.Label>
			</div>
			<DropdownMenu.Separator />
			<div class="max-h-80 overflow-y-auto thin-scrollbar">
				{#if notificationStore.notifications.length === 0}
					<div class="flex flex-col items-center justify-center h-64 text-muted-foreground">
						<Bell class="h-8 w-8 mb-2 opacity-50" />
						<p class="text-sm">No notifications</p>
					</div>
				{:else}
					{#each notificationStore.notifications as notification (notification.id)}
						{@const iconData = getSeverityIcon(notification.severity)}
						<button
							type="button"
							class="flex items-start gap-3 p-3 cursor-pointer my-1 hover:bg-muted/50 rounded-md transition-colors group w-full text-left {!notification.is_read
								? 'bg-muted/30'
								: ''}"
							onclick={() => handleNotificationClick(notification.id)}
						>
							<div class="mt-0.5">
								<iconData.icon class="h-4 w-4 {iconData.class}" />
							</div>
							<div class="flex-1 space-y-1 min-w-0">
								<p class="text-sm font-medium leading-none truncate">{notification.title}</p>
								<p class="text-xs text-muted-foreground line-clamp-2">
									{notification.message}
								</p>
								<div class="flex items-center gap-2">
									<p class="text-xs text-muted-foreground">
										{relativeTime(notification.created_at)}
									</p>
									{#if notification.notification_metadata?.url}
										<ExternalLink class="h-3 w-3 text-muted-foreground" />
									{/if}
								</div>
								{#if notification.notification_metadata?.action_label}
									<Button
										variant="secondary"
										size="sm"
										class="h-6 text-xs mt-2"
										onclick={(e) => handleActionClick(notification.id, e)}
									>
										{notification.notification_metadata.action_label}
										<ExternalLink class="ml-1 h-3 w-3" />
									</Button>
								{/if}
							</div>
							<div class="flex items-center gap-1">
								{#if !notification.is_read}
									<div class="h-2 w-2 rounded-full bg-blue-500"></div>
								{/if}
								<Button
									variant="ghost"
									size="icon"
									class="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
									onclick={(e) => handleDeleteNotification(notification.id, e)}
								>
									<Trash class="h-3 w-3" />
									<span class="sr-only">Delete</span>
								</Button>
							</div>
						</button>
					{/each}
				{/if}
			</div>
			<DropdownMenu.Separator />
			<div class="flex items-center justify-end gap-2 px-3 py-2">
				{#if notificationStore.unreadCount > 0}
					<Button
						variant="ghost"
						size="sm"
						class="h-auto p-0 text-xs"
						onclick={handleMarkAllAsRead}
					>
						Mark all as read
					</Button>
				{/if}
				{#if notificationStore.notifications.length > 0}
					<Button
						variant="ghost"
						size="sm"
						class="h-auto p-0 text-xs text-destructive hover:text-destructive"
						onclick={handleClearAll}
					>
						Clear all
					</Button>
				{/if}
				<button
					class="text-xs text-primary hover:underline"
					onclick={async () => {
						notificationsDropdownOpen = false;
						await notificationStore.loadAllNotifications();
						notificationsModalOpen = true;
					}}
				>
					View all
				</button>
			</div>
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon">
					<Plus class="h-4 w-4" />
					<span class="sr-only">Quick Actions</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end" class="w-56">
			<DropdownMenu.Label>Create New</DropdownMenu.Label>
			<DropdownMenu.Separator />
			<DropdownMenu.Item onclick={handleAddTarget}>
				<Crosshair class="mr-2 h-4 w-4" />
				Add Target
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={handleAddOrganization}>
				<Building class="mr-2 h-4 w-4" />
				Add Organization
			</DropdownMenu.Item>
			<DropdownMenu.Separator />
			<DropdownMenu.Label class="text-xs text-muted-foreground">Automation</DropdownMenu.Label>
			<DropdownMenu.Item onclick={handleNewScanEngine}>
				<Cog class="mr-2 h-4 w-4" />
				New Scan Engine
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={handleNewScanContext}>
				<Layers class="mr-2 h-4 w-4" />
				New Scan Context
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon">
					<Sun
						class="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90"
					/>
					<Moon
						class="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0"
					/>
					<span class="sr-only">Toggle theme</span>
				</Button>
			{/snippet}
		</DropdownMenu.Trigger>
		<DropdownMenu.Content align="end">
			<DropdownMenu.Item onclick={() => setMode('light')}>
				<Sun class="mr-2 h-4 w-4" />
				Light
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => setMode('dark')}>
				<Moon class="mr-2 h-4 w-4" />
				Dark
			</DropdownMenu.Item>
			<DropdownMenu.Item onclick={() => resetMode()}>
				<Monitor class="mr-2 h-4 w-4" />
				System
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
</header>

<!-- Notifications Modal -->
<Dialog.Root bind:open={notificationsModalOpen}>
	<Dialog.Content class="!max-w-none !w-[1400px] max-h-[85vh] flex flex-col">
		<Dialog.Header>
			<div class="flex items-start justify-between">
				<div>
					<Dialog.Title>All Notifications</Dialog.Title>
					<Dialog.Description>
						{notificationStore.totalCount} total notifications
						{#if notificationStore.unreadCount > 0}
							• {notificationStore.unreadCount} unread
						{/if}
					</Dialog.Description>
				</div>
				<div class="flex items-center gap-2">
					{#if notificationStore.unreadCount > 0}
						<Button variant="outline" size="sm" onclick={handleMarkAllAsRead}>
							Mark all as read
						</Button>
					{/if}
					{#if notificationStore.notifications.length > 0}
						<Button variant="outline" size="sm" onclick={handleClearAll}>
							<Trash2 class="h-4 w-4 mr-2" />
							Clear all
						</Button>
					{/if}
				</div>
			</div>
		</Dialog.Header>

		<Tabs.Root
			value={selectedFilter}
			onValueChange={(v) => (selectedFilter = v as any)}
			class="flex-1 flex flex-col overflow-hidden"
		>
			<Tabs.List class="grid grid-cols-8 w-full gap-1">
				<Tabs.Trigger value="all" class="text-xs">
					All
					<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.all}</Badge>
				</Tabs.Trigger>
				<Tabs.Trigger value="scan" class="text-xs">
					<Scan class="h-3 w-3 mr-1" />
					Scan
					{#if typeCounts.scan > 0}
						<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.scan}</Badge>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="system" class="text-xs">
					<Server class="h-3 w-3 mr-1" />
					System
					{#if typeCounts.system > 0}
						<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.system}</Badge>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="security" class="text-xs">
					<Shield class="h-3 w-3 mr-1" />
					Security
					{#if typeCounts.security > 0}
						<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.security}</Badge>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="vulnerability" class="text-xs">
					<Bug class="h-3 w-3 mr-1" />
					Vuln
					{#if typeCounts.vulnerability > 0}
						<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.vulnerability}</Badge>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="target" class="text-xs">
					<Target class="h-3 w-3 mr-1" />
					Target
					{#if typeCounts.target > 0}
						<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.target}</Badge>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="resource" class="text-xs">
					<HardDrive class="h-3 w-3 mr-1" />
					Resource
					{#if typeCounts.resource > 0}
						<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.resource}</Badge>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="integration" class="text-xs">
					<Plug class="h-3 w-3 mr-1" />
					Integration
					{#if typeCounts.integration > 0}
						<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts.integration}</Badge>
					{/if}
				</Tabs.Trigger>
			</Tabs.List>

			<div class="flex-1 overflow-y-auto thin-scrollbar mt-4">
				{#if filteredNotifications.length === 0}
					<div class="flex flex-col items-center justify-center h-64 text-muted-foreground">
						<Bell class="h-12 w-12 mb-4 opacity-50" />
						<p class="text-sm">
							No {selectedFilter === 'all' ? '' : selectedFilter} notifications
						</p>
					</div>
				{:else}
					<div class="space-y-2">
						{#each filteredNotifications as notification (notification.id)}
							{@const iconData = getSeverityIcon(notification.severity)}
							{@const TypeIcon = getTypeIcon(notification.type)}
							<button
								type="button"
								class="flex items-start gap-3 p-4 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors group text-left w-full {!notification.is_read
									? 'bg-muted/30 border-l-4 border-l-blue-500'
									: ''}"
								onclick={() => handleNotificationClick(notification.id)}
							>
								<div class="mt-0.5">
									<iconData.icon class="h-5 w-5 {iconData.class}" />
								</div>
								<div class="flex-1 space-y-2 min-w-0">
									<div class="flex items-start justify-between gap-2">
										<p class="text-sm font-medium leading-none">{notification.title}</p>
										<div class="flex items-center gap-1 shrink-0">
											<TypeIcon class="h-3.5 w-3.5 text-muted-foreground" />
											<Badge variant="outline" class="text-xs">
												{notification.type}
											</Badge>
										</div>
									</div>
									<p class="text-sm text-muted-foreground">
										{notification.message}
									</p>
									<div class="flex items-center gap-2">
										<span class="text-xs text-muted-foreground"
											>{relativeTime(notification.created_at)}</span
										>
										{#if notification.notification_metadata?.url}
											<ExternalLink class="h-3 w-3 text-muted-foreground" />
										{/if}
									</div>
									{#if notification.notification_metadata?.action_label}
										<Button
											variant="secondary"
											size="sm"
											class="h-7 text-xs"
											onclick={(e) => handleActionClick(notification.id, e)}
										>
											{notification.notification_metadata.action_label}
											<ExternalLink class="ml-1.5 h-3 w-3" />
										</Button>
									{/if}
								</div>
								<div class="flex items-center gap-1">
									{#if !notification.is_read}
										<div class="h-2 w-2 rounded-full bg-blue-500"></div>
									{/if}
									<Button
										variant="ghost"
										size="icon"
										class="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
										onclick={(e) => handleDeleteNotification(notification.id, e)}
									>
										<Trash class="h-4 w-4" />
										<span class="sr-only">Delete</span>
									</Button>
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		</Tabs.Root>
	</Dialog.Content>
</Dialog.Root>

<AddTargetModal bind:open={addTargetOpen} />

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
						<Crosshair class="mr-2 h-4 w-4" />
						<span>Add Target</span>
					</Command.Item>
					<Command.Item
						onSelect={() => {
							commandOpen = false;
							handleAddOrganization();
						}}
					>
						<Building class="mr-2 h-4 w-4" />
						<span>Add Organization</span>
					</Command.Item>
					<Command.Item
						onSelect={() => {
							commandOpen = false;
							handleNewScanEngine();
						}}
					>
						<Cog class="mr-2 h-4 w-4" />
						<span>New Scan Engine</span>
					</Command.Item>
					<Command.Item
						onSelect={() => {
							commandOpen = false;
							handleNewScanContext();
						}}
					>
						<Layers class="mr-2 h-4 w-4" />
						<span>New Scan Context</span>
					</Command.Item>
				</Command.Group>
			</Command.List>
		</Command.Root>
	</Dialog.Content>
</Dialog.Root>

<style>
	.thin-scrollbar {
		scrollbar-width: thin;
		scrollbar-color: hsl(var(--muted-foreground) / 0.3) transparent;
	}

	.thin-scrollbar::-webkit-scrollbar {
		width: 6px;
	}

	.thin-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}

	.thin-scrollbar::-webkit-scrollbar-thumb {
		background-color: hsl(var(--muted-foreground) / 0.3);
		border-radius: 3px;
	}
</style>
