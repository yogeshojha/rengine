<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
	import NotificationChannelsPanel from '$lib/components/settings/notification-channels-panel.svelte';
</script>

<svelte:head><title>{routeLabels.notifications} · reNgine</title></svelte:head>

<NotificationChannelsPanel />
