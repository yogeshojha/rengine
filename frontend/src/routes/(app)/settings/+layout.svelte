<script lang="ts">
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button/index.js';
	import { ROUTES, routeLabels, SETTINGS_SECTIONS, type SettingsSection } from '$lib/config/routes';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { Capability } from '$lib/config/capabilities';

	let { children } = $props();

	const sections = $derived(
		SETTINGS_SECTIONS.filter(
			(section) => section !== 'bounty-hub' || capabilitiesStore.has(Capability.BOUNTY_PROGRAMS)
		)
	);
	const isActive = (section: SettingsSection) =>
		page.url.pathname.startsWith(ROUTES.settings(section));
</script>

<div class="flex flex-col gap-6 md:flex-row">
	<nav aria-label="Settings" class="md:sticky md:top-20 md:w-44 md:shrink-0 md:self-start">
		<ul class="flex flex-wrap gap-1 md:flex-col">
			{#each sections as section (section)}
				<li>
					<Button
						href={ROUTES.settings(section)}
						variant={isActive(section) ? 'secondary' : 'ghost'}
						size="sm"
						class="justify-start md:w-full"
					>
						{routeLabels[section]}
					</Button>
				</li>
			{/each}
		</ul>
	</nav>
	<div class="min-w-0 flex-1">
		{@render children()}
	</div>
</div>
