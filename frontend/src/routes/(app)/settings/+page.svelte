<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	onMount(() => goto(ROUTES.settings('general')));
</script>

<svelte:head><title>{routeLabels.settings} · reNgine</title></svelte:head>
