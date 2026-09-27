<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { routeLabels } from '$lib/config/routes';
	import ApiKeysPanel from '$lib/components/settings/api-keys-panel.svelte';
</script>

<svelte:head><title>{pageTitle(routeLabels['api-keys'])}</title></svelte:head>

<ApiKeysPanel />
