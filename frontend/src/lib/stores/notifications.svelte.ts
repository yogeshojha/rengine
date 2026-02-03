import { notificationsApi, notificationSSE } from '$lib/api/notifications';
import type { Notification } from '$lib/types/notification';

interface NotificationState {
    notifications: Notification[];
    unreadCount: number;
    totalCount: number;
    isLoading: boolean;
    isConnected: boolean;
    hasLoaded: boolean;
    error: Error | null;
}

const state = $state<NotificationState>({
    notifications: [],
    unreadCount: 0,
    totalCount: 0,
    isLoading: false,
    isConnected: false,
    hasLoaded: false,
    error: null
});

let toastCallbacks: Set<(notification: Notification) => void> = new Set();

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

    get isConnected() {
        return state.isConnected;
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

    connectSSE(token?: string) {
        if (state.isConnected) {
            return;
        }

        notificationSSE.on('notification', (data: Notification) => {
            this.handleNewNotification(data, true);
        });

        notificationSSE.on('scan_status', (data: any) => {
            console.log('[SSE] Scan status:', data);
        });

        notificationSSE.on('scan_complete', (data: any) => {
            console.log('[SSE] Scan complete:', data);
        });

        notificationSSE.on('error', (error: Error) => {
            state.error = error;
            state.isConnected = false;
        });

        notificationSSE.connect(token);
        state.isConnected = true;
    },

    disconnectSSE() {
        notificationSSE.disconnect();
        state.isConnected = false;
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

    getRelativeTime(dateString: string): string {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
        return date.toLocaleDateString();
    }
};
