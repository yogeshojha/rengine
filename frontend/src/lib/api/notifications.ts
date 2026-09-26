import { api } from './client';
import type { ActionResult } from '$lib/types/action-result';
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

	markAsRead: (id: number): Promise<ActionResult> => {
		return api.patch<ActionResult>(`/notifications/${id}/read`, {});
	},

	markAllAsRead: (projectId?: string): Promise<ActionResult & { count: number }> => {
		return api.post<ActionResult & { count: number }>(
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
