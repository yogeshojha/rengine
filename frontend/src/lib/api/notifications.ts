import { api } from './client';
import type { Notification, NotificationStats } from '$lib/types/notification';
import type { PaginatedResponse } from '$lib/types/pagination';

export const notificationsApi = {
    list: (page = 1, size = 20): Promise<PaginatedResponse<Notification>> => {
        return api.get<PaginatedResponse<Notification>>(`/notifications?page=${page}&size=${size}`);
    },

    listUnread: (page = 1, size = 20): Promise<PaginatedResponse<Notification>> => {
        return api.get<PaginatedResponse<Notification>>(`/notifications/unread?page=${page}&size=${size}`);
    },

    stats: (): Promise<NotificationStats> => {
        return api.get<NotificationStats>('/notifications/stats');
    },

    markAsRead: (id: number): Promise<{ success: boolean; message: string }> => {
        return api.patch<{ success: boolean; message: string }>(`/notifications/${id}/read`, {});
    },

    markAllAsRead: (): Promise<{ success: boolean; message: string; count: number }> => {
        return api.post<{ success: boolean; message: string; count: number }>('/notifications/read-all', {});
    },

    delete: (id: number): Promise<void> => {
        return api.delete(`/notifications/${id}`);
    },

    clearAll: (): Promise<void> => {
        return api.delete('/notifications');
    },
};

export class NotificationSSE {
    private eventSource: EventSource | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 3000;
    private listeners: Map<string, Set<(data: any) => void>> = new Map();

    connect(token?: string) {
        if (this.eventSource) {
            return;
        }

        const url = token
            ? `/api/v1/notifications/stream?token=${token}`
            : '/api/v1/notifications/stream';

        this.eventSource = new EventSource(url);

        this.eventSource.addEventListener('notification', (event) => {
            const data = JSON.parse(event.data);
            this.emit('notification', data);
        });

        this.eventSource.addEventListener('scan_status', (event) => {
            const data = JSON.parse(event.data);
            this.emit('scan_status', data);
        });

        this.eventSource.addEventListener('scan_complete', (event) => {
            const data = JSON.parse(event.data);
            this.emit('scan_complete', data);
        });

        this.eventSource.addEventListener('heartbeat', () => {
            this.reconnectAttempts = 0;
        });

        this.eventSource.onerror = () => {
            this.handleError();
        };

        this.eventSource.onopen = () => {
            this.reconnectAttempts = 0;
            console.log('[SSE] Connected to notification stream');
        };
    }

    private handleError() {
        console.error('[SSE] Connection error');
        this.disconnect();

        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`[SSE] Reconnecting in ${this.reconnectDelay}ms... (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), this.reconnectDelay);
        } else {
            console.error('[SSE] Max reconnection attempts reached');
            this.emit('error', new Error('Failed to connect to notification stream'));
        }
    }

    on(event: string, callback: (data: any) => void) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event)!.add(callback);
    }

    off(event: string, callback: (data: any) => void) {
        this.listeners.get(event)?.delete(callback);
    }

    private emit(event: string, data: any) {
        this.listeners.get(event)?.forEach(callback => callback(data));
    }

    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    isConnected(): boolean {
        return this.eventSource?.readyState === EventSource.OPEN;
    }
}

export const notificationSSE = new NotificationSSE();
