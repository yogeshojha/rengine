<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	onMount(() => goto(ROUTES.scans));
</script>

<svelte:head><title>{routeLabels.automation} · reNgine</title></svelte:head>
