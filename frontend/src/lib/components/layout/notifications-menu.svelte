<script lang="ts">
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Bell from '@lucide/svelte/icons/bell';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import NotificationListItem from '$lib/components/layout/notification-list-item.svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { NOTIFICATION_TYPES, type NotificationType } from '$lib/types/notification';
	import { getTypeIcon, emptyTypeCounts } from '$lib/utilities/notification-icons';

	const TYPE_LABELS: Record<NotificationType, string> = {
		scan: 'Scan',
		system: 'System',
		security: 'Security',
		vulnerability: 'Vuln',
		target: 'Target',
		resource: 'Resource',
		integration: 'Integration'
	};

	let notificationsModalOpen = $state(false);
	let notificationsDropdownOpen = $state(false);
	let selectedFilter = $state<NotificationType | 'all'>('all');
	let clearAllOpen = $state(false);
	let clearing = $state(false);
	let viewAllLoading = $state(false);

	const filteredNotifications = $derived(
		selectedFilter === 'all'
			? notificationStore.notifications
			: notificationStore.notifications.filter((n) => n.type === selectedFilter)
	);

	const typeCounts = $derived.by(() => {
		const counts = emptyTypeCounts();
		counts.all = notificationStore.notifications.length;
		notificationStore.notifications.forEach((n) => counts[n.type]++);
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

	const openNotification = (notificationId: number) => {
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

	const handleNotificationClick = (notificationId: number) => openNotification(notificationId);

	const handleActionClick = (notificationId: number, event: Event) => {
		event.stopPropagation();
		openNotification(notificationId);
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
</script>

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
				<div
					class="flex flex-col items-center justify-center h-64 px-4 text-center text-muted-foreground"
				>
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
					<NotificationListItem
						{notification}
						variant="compact"
						onSelect={handleNotificationClick}
						onAction={handleActionClick}
						onDelete={handleDeleteNotification}
					/>
				{/each}
			{/if}
		</ScrollArea>
		<DropdownMenu.Separator />
		<div class="flex items-center justify-end gap-2 px-3 py-2">
			{#if notificationStore.unreadCount > 0}
				<Button variant="ghost" size="sm" class="h-auto p-0 text-xs" onclick={handleMarkAllAsRead}>
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
				{#each NOTIFICATION_TYPES as type (type)}
					{@const TypeIcon = getTypeIcon(type)}
					<Tabs.Trigger value={type} class="text-xs">
						<TypeIcon class="h-3 w-3 mr-1" />
						{TYPE_LABELS[type]}
						{#if typeCounts[type] > 0}
							<Badge variant="secondary" class="ml-1 text-[10px]">{typeCounts[type]}</Badge>
						{/if}
					</Tabs.Trigger>
				{/each}
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
							<Empty.Description
								>Something went wrong fetching your notifications.</Empty.Description
							>
						</Empty.Header>
						<Empty.Content>
							<Button
								variant="outline"
								size="sm"
								onclick={() => notificationStore.loadAllNotifications()}>Retry</Button
							>
						</Empty.Content>
					</Empty.Root>
				{:else if filteredNotifications.length === 0}
					<div class="flex flex-col items-center justify-center h-64 text-muted-foreground">
						<Bell class="h-12 w-12 mb-4 opacity-50" />
						<p class="text-sm">
							{selectedFilter === 'all' ? 'No notifications' : `No ${selectedFilter} notifications`}
						</p>
					</div>
				{:else}
					<div class="space-y-2">
						{#each filteredNotifications as notification (notification.id)}
							<NotificationListItem
								{notification}
								variant="full"
								onSelect={handleNotificationClick}
								onAction={handleActionClick}
								onDelete={handleDeleteNotification}
							/>
						{/each}
					</div>
				{/if}
			</ScrollArea>
		</Tabs.Root>
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
