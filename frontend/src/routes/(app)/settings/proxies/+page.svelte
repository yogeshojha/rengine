<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { routeLabels } from '$lib/config/routes';
	import ProxiesPanel from '$lib/components/settings/proxies-panel.svelte';
</script>

<svelte:head><title>{pageTitle(routeLabels.proxies)}</title></svelte:head>

<ProxiesPanel />
