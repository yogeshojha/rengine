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
