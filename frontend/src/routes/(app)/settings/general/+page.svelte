<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { routeLabels } from '$lib/config/routes';
	import InstanceSettingsPanel from '$lib/components/settings/instance-settings-panel.svelte';
</script>

<svelte:head><title>{pageTitle(routeLabels.general)}</title></svelte:head>

<InstanceSettingsPanel />
