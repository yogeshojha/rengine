import { SvelteSet } from 'svelte/reactivity';
import { notificationsApi } from '$lib/api/notifications';
import { sseStore } from '$lib/stores/sse.svelte';
import { SSEChannel, SSEEventType } from '$lib/types/sse';
import type { Notification } from '$lib/types/notification';

interface NotificationState {
	notifications: Notification[];
	unreadCount: number;
	totalCount: number;
	isLoading: boolean;
	hasLoaded: boolean;
	projectId: string | undefined;
	error: Error | null;
}

const MAX_INBOX = 200;

const state = $state<NotificationState>({
	notifications: [],
	unreadCount: 0,
	totalCount: 0,
	isLoading: false,
	hasLoaded: false,
	projectId: undefined,
	error: null
});

const toastCallbacks: SvelteSet<(notification: Notification) => void> = new SvelteSet();
let sseUnsub: (() => void) | null = null;
let resumeUnsub: (() => void) | null = null;

export const notificationStore = {
	get notifications() {
		return state.notifications;
	},

	get unreadCount() {
		return state.unreadCount;
	},

	get totalCount() {
		return state.totalCount;
	},

	get isLoading() {
		return state.isLoading;
	},

	get hasLoaded() {
		return state.hasLoaded;
	},

	get projectId() {
		return state.projectId;
	},

	get error() {
		return state.error;
	},

	subscribeToToasts(callback: (notification: Notification) => void) {
		toastCallbacks.add(callback);
		return () => toastCallbacks.delete(callback);
	},

	async loadNotifications(projectId?: string) {
		state.isLoading = true;
		state.error = null;
		state.projectId = projectId;

		try {
			const response = await notificationsApi.list(1, 50, projectId);
			state.notifications = response.items;

			const stats = await notificationsApi.stats(projectId);
			state.unreadCount = stats.unread;
			state.totalCount = stats.total;

			state.hasLoaded = true;
		} catch (error) {
			state.error = error as Error;
			console.error('[Notifications] Failed to load notifications:', error);
		} finally {
			state.isLoading = false;
		}
	},

	async loadAllNotifications() {
		state.isLoading = true;
		state.error = null;

		try {
			const stats = await notificationsApi.stats(state.projectId);
			const response = await notificationsApi.list(
				1,
				Math.min(Math.max(stats.total, 1), MAX_INBOX),
				state.projectId
			);
			state.notifications = response.items;
			state.unreadCount = stats.unread;
			state.totalCount = stats.total;
		} catch (error) {
			state.error = error as Error;
			console.error('[Notifications] Failed to load all notifications:', error);
		} finally {
			state.isLoading = false;
		}
	},

	async markAsRead(id: number) {
		if (state.notifications.find((n) => n.id === id)?.is_read) return;
		try {
			await notificationsApi.markAsRead(id);

			const notification = state.notifications.find((n) => n.id === id);
			if (notification && !notification.is_read) {
				notification.is_read = true;
				state.unreadCount = Math.max(0, state.unreadCount - 1);
			}
		} catch (error) {
			console.error('[Notifications] Failed to mark as read:', error);
		}
	},

	async markAllAsRead() {
		const result = await notificationsApi.markAllAsRead(state.projectId);

		state.notifications.forEach((n) => (n.is_read = true));
		state.unreadCount = 0;

		return result.count;
	},

	async deleteNotification(id: number) {
		await notificationsApi.delete(id);

		const notification = state.notifications.find((n) => n.id === id);
		const wasUnread = notification && !notification.is_read;

		state.notifications = state.notifications.filter((n) => n.id !== id);

		if (wasUnread) {
			state.unreadCount = Math.max(0, state.unreadCount - 1);
		}

		state.totalCount = Math.max(0, state.totalCount - 1);
	},

	async clearAll() {
		await notificationsApi.clearAll(state.projectId);
		state.notifications = [];
		state.unreadCount = 0;
		state.totalCount = 0;
	},

	subscribeSSE() {
		if (sseUnsub) return;

		sseUnsub = sseStore.on<Notification>(
			SSEChannel.BROADCAST,
			SSEEventType.NOTIFICATION,
			(data) => {
				this.handleNewNotification(data);
			}
		);
		resumeUnsub = sseStore.onResume(() => void this.loadNotifications(state.projectId));
	},

	unsubscribeSSE() {
		sseUnsub?.();
		sseUnsub = null;
		resumeUnsub?.();
		resumeUnsub = null;
	},

	reset() {
		sseUnsub?.();
		sseUnsub = null;
		resumeUnsub?.();
		resumeUnsub = null;
		state.notifications = [];
		state.unreadCount = 0;
		state.totalCount = 0;
		state.isLoading = false;
		state.hasLoaded = false;
		state.projectId = undefined;
		state.error = null;
	},

	handleNewNotification(notification: Notification) {
		if (notification.project_id && notification.project_id !== state.projectId) return;
		if (state.notifications.some((n) => n.id === notification.id)) return;

		state.notifications = [notification, ...state.notifications].slice(0, MAX_INBOX);

		if (!notification.is_read) {
			state.unreadCount++;
		}

		state.totalCount++;

		toastCallbacks.forEach((callback) => callback(notification));
	}
};
