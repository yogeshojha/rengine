<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
	import InstanceSettingsPanel from '$lib/components/settings/instance-settings-panel.svelte';
</script>

<svelte:head><title>{routeLabels.general} · reNgine</title></svelte:head>

<InstanceSettingsPanel />
