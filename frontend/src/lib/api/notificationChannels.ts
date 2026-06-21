import { api } from './client';
import type {
	NotificationChannelRead,
	NotificationChannelCreate,
	NotificationChannelUpdate
} from '$lib/types/notification-channel';

export const notificationChannelsApi = {
	list: (): Promise<NotificationChannelRead[]> => {
		return api.get<NotificationChannelRead[]>('/notification-channels');
	},

	get: (id: string): Promise<NotificationChannelRead> => {
		return api.get<NotificationChannelRead>(`/notification-channels/${id}`);
	},

	create: (data: NotificationChannelCreate): Promise<NotificationChannelRead> => {
		return api.post<NotificationChannelRead>('/notification-channels', data);
	},

	update: (id: string, data: NotificationChannelUpdate): Promise<NotificationChannelRead> => {
		return api.patch<NotificationChannelRead>(`/notification-channels/${id}`, data);
	},

	remove: (id: string): Promise<void> => {
		return api.delete(`/notification-channels/${id}`);
	},

	test: (id: string): Promise<{ success: boolean; message: string }> => {
		return api.post<{ success: boolean; message: string }>(`/notification-channels/${id}/test`);
	},

	testConfig: (data: {
		provider: string;
		config: Record<string, unknown>;
	}): Promise<{ success: boolean; message: string }> => {
		return api.post<{ success: boolean; message: string }>('/notification-channels/test', data);
	}
};
