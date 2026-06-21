<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import * as Command from '$lib/components/ui/command/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import { setMode, resetMode } from 'mode-watcher';
	import {
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
	import { goto } from '$app/navigation';
	import { targetsApi } from '$lib/api/targets';
	import type { Target as TargetEntity } from '$lib/types/target';
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { relativeTime } from '$lib/utilities/dates.js';
	import type { NotificationType, NotificationSeverity } from '$lib/types/notification';
	import { toast } from 'svelte-sonner';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import ActivityGlance from '$lib/components/activity/activity-glance.svelte';

	let commandOpen = $state(false);
	let searchQuery = $state('');
	let searchResults = $state<TargetEntity[]>([]);
	let searching = $state(false);
	$effect(() => {
		const q = searchQuery.trim();
		if (q.length < 2) {
			searchResults = [];
			searching = false;
			return;
		}
		searching = true;
		const t = setTimeout(async () => {
			try {
				searchResults = await targetsApi.searchByValue(q);
			} catch {
				searchResults = [];
			} finally {
				searching = false;
			}
		}, 250);
		return () => clearTimeout(t);
	});
	$effect(() => {
		if (!commandOpen) {
			searchQuery = '';
			searchResults = [];
		}
	});
	let notificationsModalOpen = $state(false);
	let notificationsDropdownOpen = $state(false);
	let selectedFilter = $state<NotificationType | 'all'>('all');
	let addTargetOpen = $state(false);
	let clearAllOpen = $state(false);
	let clearing = $state(false);
	let viewAllLoading = $state(false);

	const isMac =
		typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
	const searchShortcut = isMac ? '⌘K' : 'Ctrl+K';

	const getSeverityIcon = (severity: NotificationSeverity) => {
		switch (severity) {
			case 'error':
				return { icon: ShieldAlert, class: 'text-destructive' };
			case 'warning':
				return { icon: TriangleAlert, class: 'text-amber-600 dark:text-amber-500' };
			case 'success':
				return { icon: CircleCheck, class: 'text-foreground' };
			default:
				return { icon: Info, class: 'text-chart-1' };
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

	const navigateToUrl = (url: string, openNewTab?: boolean) => {
		if (openNewTab) {
			window.open(url, '_blank', 'noopener,noreferrer');
			return;
		}
		const isInternal = url.startsWith('/') || url.startsWith(window.location.origin);
		if (isInternal) {
			goto(url);
		} else {
			window.open(url, '_blank', 'noopener,noreferrer');
		}
	};

	const handleNotificationClick = (notificationId: number) => {
		const notification = notificationStore.notifications.find((n) => n.id === notificationId);
		if (!notification) return;

		notificationStore.markAsRead(notificationId);

		const metadata = notification.notification_metadata;
		if (metadata?.url) {
			notificationsDropdownOpen = false;
			notificationsModalOpen = false;
			navigateToUrl(metadata.url, metadata.open_new_tab);
		}
	};

	const handleActionClick = (notificationId: number, event: Event) => {
		event.stopPropagation();

		const notification = notificationStore.notifications.find((n) => n.id === notificationId);
		if (!notification) return;

		notificationStore.markAsRead(notificationId);

		const metadata = notification.notification_metadata;
		if (metadata?.url) {
			notificationsDropdownOpen = false;
			notificationsModalOpen = false;
			navigateToUrl(metadata.url, metadata.open_new_tab);
		}
	};

	const handleDeleteNotification = async (id: number, event: Event) => {
		event.stopPropagation();
		try {
			await notificationStore.deleteNotification(id);
		} catch {
			toast.error("Couldn't delete notification — try again");
		}
	};

	const handleMarkAllAsRead = async () => {
		try {
			await notificationStore.markAllAsRead();
		} catch {
			toast.error("Couldn't mark notifications as read — try again");
		}
	};

	const confirmClearAll = async () => {
		clearing = true;
		try {
			await notificationStore.clearAll();
			clearAllOpen = false;
		} catch {
			toast.error("Couldn't clear notifications — try again");
		} finally {
			clearing = false;
		}
	};

	const handleViewAll = async () => {
		notificationsDropdownOpen = false;
		viewAllLoading = true;
		try {
			await notificationStore.loadAllNotifications();
			notificationsModalOpen = true;
		} finally {
			viewAllLoading = false;
		}
	};

	const retryLoad = () => notificationStore.loadNotifications();

	$effect(() => {
		const handleKeydown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
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

	const handleNewScanEngine = () => {
		goto('/automation/engines');
	};

	const handleNewScanContext = () => {
		goto('/automation/contexts');
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

	<Button
		variant="outline"
		class="relative h-9 w-full justify-start rounded-md text-sm text-muted-foreground sm:w-64 md:w-80"
		onclick={() => (commandOpen = true)}
	>
		<SearchIcon class="mr-2 h-4 w-4" />
		<span>Search...</span>
		<kbd
			class="pointer-events-none absolute right-1.5 top-1.5 hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex"
		>
			{searchShortcut}
		</kbd>
	</Button>

	<DropdownMenu.Root bind:open={notificationsDropdownOpen}>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon" class="relative" title="Notifications">
					<Bell class="h-4 w-4" />
					{#if notificationStore.unreadCount > 0}
						<Badge
							class="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-[10px] bg-destructive text-destructive-foreground"
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
			<ScrollArea class="h-80">
				{#if notificationStore.isLoading && !notificationStore.hasLoaded}
					<div class="space-y-1 p-1">
						{#each Array(4) as _, i (i)}
							<div class="flex items-start gap-3 p-3">
								<Skeleton class="h-4 w-4 rounded-full" />
								<div class="flex-1 space-y-2">
									<Skeleton class="h-3 w-3/4" />
									<Skeleton class="h-3 w-full" />
									<Skeleton class="h-3 w-1/3" />
								</div>
							</div>
						{/each}
					</div>
				{:else if notificationStore.error}
					<div class="flex flex-col items-center justify-center h-64 px-4 text-center text-muted-foreground">
						<TriangleAlert class="h-8 w-8 mb-2 text-destructive" />
						<p class="text-sm">Couldn't load notifications</p>
						<Button variant="outline" size="sm" class="mt-3" onclick={retryLoad}>Retry</Button>
					</div>
				{:else if notificationStore.notifications.length === 0}
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
									<div class="h-2 w-2 rounded-full bg-chart-1"></div>
								{/if}
								<Button
									variant="ghost"
									size="icon"
									class="h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
									onclick={(e) => handleDeleteNotification(notification.id, e)}
								>
									<Trash class="h-3 w-3" />
									<span class="sr-only">Delete notification</span>
								</Button>
							</div>
						</button>
					{/each}
				{/if}
			</ScrollArea>
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
						onclick={() => (clearAllOpen = true)}
					>
						Clear all
					</Button>
				{/if}
				<Button
					variant="link"
					size="sm"
					class="h-auto p-0 text-xs"
					disabled={viewAllLoading}
					onclick={handleViewAll}
				>
					{#if viewAllLoading}
						<Spinner class="mr-1 h-3 w-3" />
					{/if}
					View all
				</Button>
			</div>
		</DropdownMenu.Content>
	</DropdownMenu.Root>

	<DropdownMenu.Root>
		<DropdownMenu.Trigger>
			{#snippet child({ props })}
				<Button {...props} variant="ghost" size="icon" title="Quick actions">
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
			<DropdownMenu.Item disabled class="justify-between">
				<span class="flex items-center">
					<Building class="mr-2 h-4 w-4" />
					Add Organization
				</span>
				<Badge variant="secondary" class="text-[10px]">Soon</Badge>
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
				<Button {...props} variant="ghost" size="icon" title="Toggle theme">
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

<Dialog.Root bind:open={notificationsModalOpen}>
	<Dialog.Content class="w-[calc(100%-2rem)] max-w-5xl max-h-[85vh] flex flex-col">
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
						<Button
							variant="outline"
							size="sm"
							class="text-destructive hover:text-destructive"
							onclick={() => (clearAllOpen = true)}
						>
							<Trash2 class="h-4 w-4 mr-2" />
							Clear all
						</Button>
					{/if}
				</div>
			</div>
		</Dialog.Header>

		<Tabs.Root
			value={selectedFilter}
			onValueChange={(v) => (selectedFilter = v as NotificationType | 'all')}
			class="flex-1 min-h-0 flex flex-col overflow-hidden"
		>
			<Tabs.List class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-8 w-full h-auto gap-1">
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

			<ScrollArea class="mt-4 flex-1 min-h-0">
				{#if notificationStore.isLoading}
					<div class="space-y-2">
						{#each Array(5) as _, i (i)}
							<div class="flex items-start gap-3 p-4 rounded-lg border">
								<Skeleton class="h-5 w-5 rounded-full" />
								<div class="flex-1 space-y-2">
									<Skeleton class="h-4 w-1/2" />
									<Skeleton class="h-4 w-full" />
									<Skeleton class="h-3 w-1/4" />
								</div>
							</div>
						{/each}
					</div>
				{:else if notificationStore.error}
					<Empty.Root class="h-64">
						<Empty.Header>
							<Empty.Media variant="icon">
								<TriangleAlert class="text-destructive" />
							</Empty.Media>
							<Empty.Title>Couldn't load notifications</Empty.Title>
							<Empty.Description>Something went wrong fetching your notifications.</Empty.Description>
						</Empty.Header>
						<Empty.Content>
							<Button variant="outline" size="sm" onclick={() => notificationStore.loadAllNotifications()}
								>Retry</Button
							>
						</Empty.Content>
					</Empty.Root>
				{:else if filteredNotifications.length === 0}
					<div class="flex flex-col items-center justify-center h-64 text-muted-foreground">
						<Bell class="h-12 w-12 mb-4 opacity-50" />
						<p class="text-sm">
							{selectedFilter === 'all'
								? 'No notifications'
								: `No ${selectedFilter} notifications`}
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
									? 'bg-muted/30 border-l-4 border-l-chart-1'
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
										<div class="h-2 w-2 rounded-full bg-chart-1"></div>
									{/if}
									<Button
										variant="ghost"
										size="icon"
										class="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
										onclick={(e) => handleDeleteNotification(notification.id, e)}
									>
										<Trash class="h-4 w-4" />
										<span class="sr-only">Delete notification</span>
									</Button>
								</div>
							</button>
						{/each}
					</div>
				{/if}
			</ScrollArea>
		</Tabs.Root>
	</Dialog.Content>
</Dialog.Root>

<AddTargetModal bind:open={addTargetOpen} />

<Dialog.Root bind:open={commandOpen}>
	<Dialog.Content class="overflow-hidden p-0 shadow-lg sm:max-w-[550px]">
		<Command.Root shouldFilter={false} class="[&_[data-cmd-input-wrapper]]:border-b">
			<Command.Input bind:value={searchQuery} placeholder="Search targets or run an action..." />
			<Command.List>
				{#if searchQuery.trim().length >= 2}
					{#if searching}
						<div
							class="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground"
						>
							<Spinner class="size-4" /> Searching…
						</div>
					{:else if searchResults.length === 0}
						<div class="py-6 text-center text-sm text-muted-foreground">No targets found.</div>
					{:else}
						<Command.Group heading="Targets">
							{#each searchResults as t (t.id)}
								<Command.Item
									value={t.id}
									onSelect={() => {
										commandOpen = false;
										goto('/targets/' + t.id);
									}}
								>
									<Crosshair class="mr-2 h-4 w-4 shrink-0" />
									<span class="truncate">{t.target_value}</span>
								</Command.Item>
							{/each}
						</Command.Group>
					{/if}
				{:else}
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
						<Command.Item disabled class="justify-between">
							<span class="flex items-center">
								<Building class="mr-2 h-4 w-4" />
								Add Organization
							</span>
							<Badge variant="secondary" class="text-[10px]">Soon</Badge>
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
				{/if}
			</Command.List>
		</Command.Root>
	</Dialog.Content>
</Dialog.Root>

<DeleteConfirmationDialog
	bind:open={clearAllOpen}
	title="Clear all notifications?"
	description={`This permanently deletes all ${notificationStore.totalCount} notifications, including any you haven't triaged. This can't be undone.`}
	confirmLabel="Clear all"
	isDeleting={clearing}
	onOpenChange={(o) => (clearAllOpen = o)}
	onConfirm={confirmClearAll}
/>
