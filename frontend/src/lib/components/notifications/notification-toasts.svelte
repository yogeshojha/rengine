<script lang="ts">
	import { notificationStore } from '$lib/stores/notifications.svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { onMount } from 'svelte';
	import type { MessageLevel } from '$lib/types/message-level';
	import { headline } from '$lib/utilities/notifications';

	const INTERRUPTS: MessageLevel[] = ['error'];
	const DURATION: Partial<Record<MessageLevel, number>> = { error: 10000 };

	function isSameOrigin(url: string): boolean {
		try {
			return new URL(url, window.location.origin).origin === window.location.origin;
		} catch {
			return false;
		}
	}

	onMount(() => {
		const unsubscribe = notificationStore.subscribeToToasts((notification) => {
			if (!INTERRUPTS.includes(notification.severity)) return;

			const metadata = notification.notification_metadata;
			toast.error(notification.title, {
				description: headline(notification.message),
				action: metadata?.url
					? {
							label: metadata.action_label ?? 'View',
							onClick: () => {
								void notificationStore.markAsRead(notification.id);
								const url = metadata.url as string;
								if (metadata.open_new_tab || !isSameOrigin(url)) {
									window.open(url, '_blank', 'noopener,noreferrer');
								} else {
									void goto(url);
								}
							}
						}
					: undefined,
				duration: DURATION[notification.severity] ?? 5000
			});
		});

		return () => unsubscribe();
	});
</script>
