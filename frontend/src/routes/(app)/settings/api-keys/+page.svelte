<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
	import ApiKeysPanel from '$lib/components/settings/api-keys-panel.svelte';
</script>

<svelte:head><title>{routeLabels['api-keys']} · reNgine</title></svelte:head>

<ApiKeysPanel />
