<script lang="ts">
	import AskPage from '$lib/components/ask/ask-page.svelte';
	import { routeLabels } from '$lib/config/routes';
	import { pageTitle } from '$lib/utilities/page-title';
</script>

<svelte:head><title>{pageTitle(routeLabels.ask)}</title></svelte:head>

<AskPage />
