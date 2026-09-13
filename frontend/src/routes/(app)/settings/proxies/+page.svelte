<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
	import ProxiesPanel from '$lib/components/settings/proxies-panel.svelte';
</script>

<svelte:head><title>{routeLabels.proxies} · reNgine</title></svelte:head>

<ProxiesPanel />
