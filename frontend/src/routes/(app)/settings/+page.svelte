<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	onMount(() => goto(ROUTES.settings('general'), { replaceState: true }));
</script>

<svelte:head><title>{pageTitle(routeLabels.settings)}</title></svelte:head>
