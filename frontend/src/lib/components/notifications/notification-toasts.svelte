<script lang="ts">
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';

	onMount(() => {
		const unsubscribe = notificationStore.subscribeToToasts((notification) => {
			const metadata = notification.notification_metadata;

			const toastFunction = {
				success: toast.success,
				error: toast.error,
				warning: toast.warning,
				info: toast.info
			}[notification.severity] || toast;

			toastFunction(notification.title, {
				description: notification.message,
				action: metadata?.action_label
					? {
							label: metadata.action_label,
							onClick: () => {
								void notificationStore.markAsRead(notification.id);
								if (metadata.url) {
									if (metadata.open_new_tab) {
										window.open(metadata.url, '_blank', 'noopener,noreferrer');
									} else {
										window.location.href = metadata.url;
									}
								}
							}
						}
					: undefined,
				duration: 5000
			});
		});

		return () => unsubscribe();
	});
</script>
