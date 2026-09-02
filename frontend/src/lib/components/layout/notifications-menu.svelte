<script lang="ts">
	import * as Popover from '$lib/components/ui/popover/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Dialog from '$lib/components/ui/dialog/index.js';
	import * as Empty from '$lib/components/ui/empty/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Bell from '@lucide/svelte/icons/bell';
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import Inbox from '@lucide/svelte/icons/inbox';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import NotificationListItem from '$lib/components/layout/notification-list-item.svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import {
		NOTIFICATION_TYPES,
		NOTIFICATION_TYPE_LABELS,
		type NotificationType
	} from '$lib/types/notification';
	import { getTypeIcon, emptyTypeCounts } from '$lib/utilities/notification-icons';
	import {
		groupByRecency,
		highestSeverity,
		UNREAD_BADGE_CLASS
	} from '$lib/utilities/notifications';
	import { ROUTES } from '$lib/config/routes';

	type InboxTab = 'unread' | 'all';

	let popoverOpen = $state(false);
	let modalOpen = $state(false);
	let tab = $state<InboxTab>('all');
	let selectedFilter = $state<NotificationType | 'all'>('all');
	let clearAllOpen = $state(false);
	let clearing = $state(false);
	let viewAllLoading = $state(false);

	const unread = $derived(notificationStore.notifications.filter((n) => !n.is_read));
	const inboxList = $derived(tab === 'unread' ? unread : notificationStore.notifications);
	const inboxGroups = $derived(groupByRecency(inboxList));
	const badgeClass = $derived(UNREAD_BADGE_CLASS[highestSeverity(unread) ?? 'info']);
	const badgeText = $derived(
		notificationStore.unreadCount > 99 ? '99+' : String(notificationStore.unreadCount)
	);

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

	function onPopoverChange(open: boolean) {
		popoverOpen = open;
		if (open) tab = notificationStore.unreadCount > 0 ? 'unread' : 'all';
	}

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
			popoverOpen = false;
			modalOpen = false;
			navigateToUrl(metadata.url, metadata.open_new_tab);
		}
	};

	const handleActionClick = (notificationId: number, event: Event) => {
		event.stopPropagation();
		openNotification(notificationId);
	};

	const handleMarkRead = (id: number, event: Event) => {
		event.stopPropagation();
		notificationStore.markAsRead(id);
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
		popoverOpen = false;
		viewAllLoading = true;
		try {
			await notificationStore.loadAllNotifications();
			modalOpen = true;
		} finally {
			viewAllLoading = false;
		}
	};

	const openSettings = () => {
		popoverOpen = false;
		goto(ROUTES.settings('notifications'));
	};

	const retryLoad = () => notificationStore.loadNotifications();
</script>

{#snippet skeletonRows(count: number)}
	<div class="space-y-1 py-1">
		{#each Array(count) as _, i (i)}
			<div class="flex items-start gap-3 px-4 py-2.5">
				<Skeleton class="size-7 rounded-md" />
				<div class="flex-1 space-y-2">
					<Skeleton class="h-3 w-3/4" />
					<Skeleton class="h-3 w-full" />
					<Skeleton class="h-2.5 w-1/4" />
				</div>
			</div>
		{/each}
	</div>
{/snippet}

<Popover.Root open={popoverOpen} onOpenChange={onPopoverChange}>
	<Popover.Trigger>
		{#snippet child({ props })}
			<Button {...props} variant="ghost" size="icon" class="relative" aria-label="Notifications">
				<Bell class="size-4" />
				{#if notificationStore.unreadCount > 0}
					<span
						class="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full px-1 font-mono text-[10px] leading-none font-semibold tabular-nums ring-2 ring-background {badgeClass}"
					>
						{badgeText}
					</span>
				{/if}
			</Button>
		{/snippet}
	</Popover.Trigger>
	<Popover.Content
		align="end"
		sideOffset={8}
		onOpenAutoFocus={(e) => e.preventDefault()}
		class="w-[min(24rem,calc(100vw-1rem))] overflow-hidden p-0"
	>
		<div class="flex items-center justify-between gap-2 px-4 pt-3 pb-2">
			<div class="flex items-center gap-2">
				<span class="text-sm font-semibold">Notifications</span>
				{#if notificationStore.unreadCount > 0}
					<Badge variant="info" class="h-5 px-1.5 text-[10px] tabular-nums">
						{notificationStore.unreadCount} new
					</Badge>
				{/if}
			</div>
			<div class="flex items-center">
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="size-7 text-muted-foreground hover:text-foreground"
								disabled={notificationStore.unreadCount === 0}
								onclick={handleMarkAllAsRead}
								aria-label="Mark all as read"
							>
								<CheckCheck class="size-3.5" />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="bottom">Mark all as read</Tooltip.Content>
				</Tooltip.Root>
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								class="size-7 text-muted-foreground hover:text-foreground"
								onclick={openSettings}
								aria-label="Notification settings"
							>
								<Settings2 class="size-3.5" />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="bottom">Notification settings</Tooltip.Content>
				</Tooltip.Root>
			</div>
		</div>

		<Tabs.Root value={tab} onValueChange={(v) => (tab = v as InboxTab)} class="gap-0">
			<Tabs.List class="mx-4 mb-1 grid h-8 w-auto grid-cols-2">
				<Tabs.Trigger value="unread" class="text-xs">
					Unread
					{#if notificationStore.unreadCount > 0}
						<span class="font-mono text-[10px] text-muted-foreground tabular-nums">
							{notificationStore.unreadCount}
						</span>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="all" class="text-xs">
					All
					<span class="font-mono text-[10px] text-muted-foreground tabular-nums">
						{notificationStore.totalCount}
					</span>
				</Tabs.Trigger>
			</Tabs.List>
		</Tabs.Root>

		<ScrollArea class="border-t [&_[data-slot=scroll-area-viewport]]:max-h-[min(60vh,26rem)]">
			{#if notificationStore.isLoading && !notificationStore.hasLoaded}
				{@render skeletonRows(4)}
			{:else if notificationStore.error}
				<Empty.Root class="h-64 border-none">
					<Empty.Header>
						<Empty.Media variant="icon">
							<TriangleAlert class="text-destructive" />
						</Empty.Media>
						<Empty.Title class="text-sm">Couldn't load notifications</Empty.Title>
					</Empty.Header>
					<Empty.Content>
						<Button variant="outline" size="sm" onclick={retryLoad}>Retry</Button>
					</Empty.Content>
				</Empty.Root>
			{:else if inboxList.length === 0}
				<Empty.Root class="h-64 border-none">
					<Empty.Header>
						<Empty.Media variant="icon">
							{#if tab === 'unread'}
								<CheckCheck class="text-success" />
							{:else}
								<Inbox class="text-muted-foreground" />
							{/if}
						</Empty.Media>
						<Empty.Title class="text-sm">
							{tab === 'unread' ? "You're all caught up" : 'No notifications yet'}
						</Empty.Title>
						<Empty.Description class="text-xs">
							{tab === 'unread'
								? 'New alerts and scan results land here.'
								: 'Scan results, findings and system events will appear here.'}
						</Empty.Description>
					</Empty.Header>
				</Empty.Root>
			{:else}
				<div class="pb-1">
					{#each inboxGroups as group (group.label)}
						<div
							class="sticky top-0 z-10 bg-popover/95 px-4 pt-2.5 pb-1 text-[10px] font-semibold tracking-[0.1em] text-muted-foreground/70 uppercase backdrop-blur"
						>
							{group.label}
						</div>
						{#each group.items as notification (notification.id)}
							<NotificationListItem
								{notification}
								variant="compact"
								onSelect={openNotification}
								onAction={handleActionClick}
								onDelete={handleDeleteNotification}
								onMarkRead={handleMarkRead}
							/>
						{/each}
					{/each}
				</div>
			{/if}
		</ScrollArea>

		<div
			class="relative z-10 flex items-center justify-between gap-2 border-t bg-muted/40 px-3 py-2"
		>
			<Button
				variant="ghost"
				size="sm"
				class="h-7 px-2 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
				disabled={notificationStore.notifications.length === 0}
				onclick={() => (clearAllOpen = true)}
			>
				<Trash2 class="size-3" />
				Clear all
			</Button>
			<Button
				variant="secondary"
				size="sm"
				class="h-7 px-2.5 text-xs"
				disabled={viewAllLoading}
				onclick={handleViewAll}
			>
				{#if viewAllLoading}
					<Spinner class="size-3" />
				{/if}
				View all
				<ArrowRight class="size-3" />
			</Button>
		</div>
	</Popover.Content>
</Popover.Root>

<Dialog.Root bind:open={modalOpen}>
	<Dialog.Content class="flex max-h-[85vh] w-[calc(100%-2rem)] max-w-4xl flex-col">
		<Dialog.Header>
			<div class="flex items-start justify-between gap-4">
				<div>
					<Dialog.Title>All notifications</Dialog.Title>
					<Dialog.Description>
						{notificationStore.totalCount} total
						{#if notificationStore.unreadCount > 0}
							· {notificationStore.unreadCount} unread
						{/if}
					</Dialog.Description>
				</div>
				<div class="flex items-center gap-2">
					{#if notificationStore.unreadCount > 0}
						<Button variant="outline" size="sm" onclick={handleMarkAllAsRead}>
							<CheckCheck class="size-3.5" />
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
							<Trash2 class="size-3.5" />
							Clear all
						</Button>
					{/if}
				</div>
			</div>
		</Dialog.Header>

		<Tabs.Root
			value={selectedFilter}
			onValueChange={(v) => (selectedFilter = v as NotificationType | 'all')}
			class="flex min-h-0 flex-1 flex-col overflow-hidden"
		>
			<Tabs.List class="flex h-auto w-full flex-wrap justify-start gap-1">
				<Tabs.Trigger value="all" class="flex-none text-xs">
					All
					<span class="font-mono text-[10px] text-muted-foreground tabular-nums">
						{typeCounts.all}
					</span>
				</Tabs.Trigger>
				{#each NOTIFICATION_TYPES as type (type)}
					{@const TypeIcon = getTypeIcon(type)}
					<Tabs.Trigger value={type} class="flex-none text-xs">
						<TypeIcon class="size-3" />
						{NOTIFICATION_TYPE_LABELS[type]}
						{#if typeCounts[type] > 0}
							<span class="font-mono text-[10px] text-muted-foreground tabular-nums">
								{typeCounts[type]}
							</span>
						{/if}
					</Tabs.Trigger>
				{/each}
			</Tabs.List>

			<ScrollArea class="mt-3 min-h-0 flex-1">
				{#if notificationStore.isLoading}
					<div class="space-y-2">
						{#each Array(5) as _, i (i)}
							<div class="flex items-start gap-3 rounded-lg border p-4">
								<Skeleton class="size-8 rounded-md" />
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
					<Empty.Root class="h-64 border-none">
						<Empty.Header>
							<Empty.Media variant="icon">
								<Inbox class="text-muted-foreground" />
							</Empty.Media>
							<Empty.Title class="text-sm">
								{selectedFilter === 'all'
									? 'No notifications'
									: `No ${NOTIFICATION_TYPE_LABELS[selectedFilter].toLowerCase()} notifications`}
							</Empty.Title>
						</Empty.Header>
					</Empty.Root>
				{:else}
					<div class="space-y-2 pr-3">
						{#each filteredNotifications as notification (notification.id)}
							<NotificationListItem
								{notification}
								variant="full"
								onSelect={openNotification}
								onAction={handleActionClick}
								onDelete={handleDeleteNotification}
								onMarkRead={handleMarkRead}
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
