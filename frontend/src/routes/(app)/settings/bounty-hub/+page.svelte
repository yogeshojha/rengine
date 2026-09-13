<script lang="ts">
	import { routeLabels } from '$lib/config/routes';
	import BountyHubPanel from '$lib/components/settings/bounty-hub-panel.svelte';
</script>

<svelte:head><title>{routeLabels['bounty-hub']} · reNgine</title></svelte:head>

<div class="space-y-6">
	<div class="max-w-2xl">
		<h2 class="text-lg font-semibold tracking-tight">Bounty Hub</h2>
		<p class="mt-1 text-sm text-muted-foreground">
			Program sources and the events recorded when a program changes.
		</p>
	</div>
	<BountyHubPanel />
</div>
