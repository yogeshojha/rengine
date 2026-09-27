<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { routeLabels } from '$lib/config/routes';
	import NotificationChannelsPanel from '$lib/components/settings/notification-channels-panel.svelte';
</script>

<svelte:head><title>{pageTitle(routeLabels.notifications)}</title></svelte:head>

<NotificationChannelsPanel />
