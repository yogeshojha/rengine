import { api } from './client';
import { crudApi } from './crud';
import type { ActionResult } from '$lib/types/action-result';
import type {
	NotificationChannelRead,
	NotificationChannelCreate,
	NotificationChannelUpdate
} from '$lib/types/notification-channel';

export const notificationChannelsApi = {
	...crudApi<NotificationChannelRead, NotificationChannelCreate, NotificationChannelUpdate>(
		'/notification-channels'
	),

	testConfig: (data: {
		provider: string;
		config: Record<string, unknown>;
	}): Promise<ActionResult> => {
		return api.post<ActionResult>('/notification-channels/test', data);
	}
};
