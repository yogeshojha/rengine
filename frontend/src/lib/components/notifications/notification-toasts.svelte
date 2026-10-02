<script lang="ts">
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';
	import type { MessageLevel } from '$lib/types/message-level';
	import { headline, openNotificationUrl } from '$lib/utilities/notifications';

	const INTERRUPTS: MessageLevel[] = ['error'];
	const ERROR_TOAST_MS = 10000;

	onMount(() => {
		const unsubscribe = notificationStore.subscribeToToasts((notification) => {
			if (!INTERRUPTS.includes(notification.severity)) return;

			const metadata = notification.notification_metadata;
			toast.error(notification.title, {
				description: headline(notification.message),
				action: metadata?.url
					? {
							label: 'Open',
							onClick: () => {
								void notificationStore.markAsRead(notification.id);
								openNotificationUrl(metadata.url as string);
							}
						}
					: undefined,
				duration: ERROR_TOAST_MS
			});
		});

		return () => unsubscribe();
	});
</script>
