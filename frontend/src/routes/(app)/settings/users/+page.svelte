<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
	import { pageTitle } from '$lib/utilities/page-title';
	import UsersPanel from '$lib/components/settings/users-panel.svelte';
</script>

<svelte:head><title>{pageTitle(routeLabels.users)}</title></svelte:head>

<UsersPanel />
