import { api } from './client';
import type { Notification, NotificationStats } from '$lib/types/notification';
import type { PaginatedResponse } from '$lib/types/pagination';

const scope = (projectId?: string) => (projectId ? `&project_id=${projectId}` : '');

export const notificationsApi = {
	list: (page = 1, size = 20, projectId?: string): Promise<PaginatedResponse<Notification>> => {
		return api.get<PaginatedResponse<Notification>>(
			`/notifications?page=${page}&size=${size}${scope(projectId)}`
		);
	},

	listUnread: (
		page = 1,
		size = 20,
		projectId?: string
	): Promise<PaginatedResponse<Notification>> => {
		return api.get<PaginatedResponse<Notification>>(
			`/notifications/unread?page=${page}&size=${size}${scope(projectId)}`
		);
	},

	stats: (projectId?: string): Promise<NotificationStats> => {
		return api.get<NotificationStats>(
			`/notifications/stats${projectId ? `?project_id=${projectId}` : ''}`
		);
	},

	markAsRead: (id: number): Promise<{ success: boolean; message: string }> => {
		return api.patch<{ success: boolean; message: string }>(`/notifications/${id}/read`, {});
	},

	markAllAsRead: (
		projectId?: string
	): Promise<{ success: boolean; message: string; count: number }> => {
		return api.post<{ success: boolean; message: string; count: number }>(
			`/notifications/read-all${projectId ? `?project_id=${projectId}` : ''}`,
			{}
		);
	},

	delete: (id: number): Promise<void> => {
		return api.delete(`/notifications/${id}`);
	},

	clearAll: (projectId?: string): Promise<void> => {
		return api.delete(`/notifications${projectId ? `?project_id=${projectId}` : ''}`);
	}
};
