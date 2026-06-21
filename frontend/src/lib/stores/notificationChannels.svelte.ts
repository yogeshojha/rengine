import { notificationChannelsApi } from '$lib/api/notificationChannels';
import type {
	NotificationChannelRead,
	NotificationChannelCreate,
	NotificationChannelUpdate
} from '$lib/types/notification-channel';
import { toast } from 'svelte-sonner';

function createNotificationChannelsStore() {
	let channels = $state<NotificationChannelRead[]>([]);
	let isLoading = $state(false);
	let hasFetched = $state(false);

	return {
		get channels() {
			return channels;
		},
		get isLoading() {
			return isLoading;
		},
		get hasFetched() {
			return hasFetched;
		},

		async fetch() {
			if (isLoading) return;
			isLoading = true;
			try {
				channels = await notificationChannelsApi.list();
				hasFetched = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to fetch notification channels');
			} finally {
				isLoading = false;
			}
		},

		async create(data: NotificationChannelCreate): Promise<NotificationChannelRead | null> {
			try {
				const created = await notificationChannelsApi.create(data);
				channels = [...channels, created];
				return created;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to create notification channel');
				return null;
			}
		},

		async update(
			id: string,
			data: NotificationChannelUpdate
		): Promise<NotificationChannelRead | null> {
			try {
				const updated = await notificationChannelsApi.update(id, data);
				channels = channels.map((c) => (c.id === id ? updated : c));
				return updated;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to update notification channel');
				return null;
			}
		},

		async remove(id: string): Promise<boolean> {
			try {
				await notificationChannelsApi.remove(id);
				channels = channels.filter((c) => c.id !== id);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to delete notification channel');
				return false;
			}
		},

		async test(id: string): Promise<{ success: boolean; message: string } | null> {
			try {
				const result = await notificationChannelsApi.test(id);
				channels = channels.map((c) =>
					c.id === id
						? {
								...c,
								last_test_at: new Date().toISOString(),
								last_test_ok: result.success,
								last_test_message: result.message
							}
						: c
				);
				return result;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to test notification channel');
				return null;
			}
		},

		clear() {
			channels = [];
			hasFetched = false;
		}
	};
}

export const notificationChannelsStore = createNotificationChannelsStore();
