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
    error: Error | null;
}

const state = $state<NotificationState>({
    notifications: [],
    unreadCount: 0,
    totalCount: 0,
    isLoading: false,
    hasLoaded: false,
    error: null
});

let toastCallbacks: Set<(notification: Notification) => void> = new Set();
let sseUnsub: (() => void) | null = null;

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

    get error() {
        return state.error;
    },

    subscribeToToasts(callback: (notification: Notification) => void) {
        toastCallbacks.add(callback);
        return () => toastCallbacks.delete(callback);
    },

    async loadNotifications(page = 1, size = 50) {
        state.isLoading = true;
        state.error = null;

        try {
            const response = await notificationsApi.list(page, size);
            state.notifications = response.items;

            const stats = await notificationsApi.stats();
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
            const stats = await notificationsApi.stats();
            const response = await notificationsApi.list(1, stats.total);
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

    async updateStats() {
        try {
            const stats = await notificationsApi.stats();
            state.unreadCount = stats.unread;
        } catch (error) {
            console.error('[Notifications] Failed to update stats:', error);
        }
    },

    async markAsRead(id: number) {
        try {
            await notificationsApi.markAsRead(id);

            const notification = state.notifications.find(n => n.id === id);
            if (notification && !notification.is_read) {
                notification.is_read = true;
                state.unreadCount = Math.max(0, state.unreadCount - 1);
            }
        } catch (error) {
            console.error('[Notifications] Failed to mark as read:', error);
        }
    },

    async markAllAsRead() {
        try {
            const result = await notificationsApi.markAllAsRead();

            state.notifications.forEach(n => n.is_read = true);
            state.unreadCount = 0;

            return result.count;
        } catch (error) {
            console.error('[Notifications] Failed to mark all as read:', error);
            throw error;
        }
    },

    async deleteNotification(id: number) {
        try {
            await notificationsApi.delete(id);

            const notification = state.notifications.find(n => n.id === id);
            const wasUnread = notification && !notification.is_read;

            state.notifications = state.notifications.filter(n => n.id !== id);

            if (wasUnread) {
                state.unreadCount = Math.max(0, state.unreadCount - 1);
            }

            state.totalCount = Math.max(0, state.totalCount - 1);
        } catch (error) {
            console.error('[Notifications] Failed to delete notification:', error);
            throw error;
        }
    },

    async clearAll() {
        try {
            await notificationsApi.clearAll();
            state.notifications = [];
            state.unreadCount = 0;
            state.totalCount = 0;
        } catch (error) {
            console.error('[Notifications] Failed to clear all:', error);
            throw error;
        }
    },

    /**
     * Subscribe to notifications
     */
    subscribeSSE() {
        if (sseUnsub) return;

        sseUnsub = sseStore.on<Notification>(SSEChannel.BROADCAST, SSEEventType.NOTIFICATION, (data) => {
            this.handleNewNotification(data, true);
        });
    },

    /**
     * Unsubscribe from SSE notifications.
     */
    unsubscribeSSE() {
        sseUnsub?.();
        sseUnsub = null;
    },

    reset() {
        sseUnsub?.();
        sseUnsub = null;
        state.notifications = [];
        state.unreadCount = 0;
        state.totalCount = 0;
        state.isLoading = false;
        state.hasLoaded = false;
        state.error = null;
    },

    handleNewNotification(notification: Notification, fromSSE: boolean = true) {
        state.notifications = [notification, ...state.notifications];

        if (!notification.is_read) {
            state.unreadCount++;
        }

        state.totalCount++;

        if (fromSSE) {
            toastCallbacks.forEach(callback => callback(notification));
        }
    },
};
