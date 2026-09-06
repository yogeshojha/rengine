<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack, type Component } from 'svelte';
	import ShieldAlertIcon from '@lucide/svelte/icons/shield-alert';
	import WholeWordIcon from '@lucide/svelte/icons/whole-word';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import NucleiLibrary from '$lib/components/arsenal/nuclei-library.svelte';
	import WordlistLibrary from '$lib/components/arsenal/wordlist-library.svelte';
	import { ARSENAL_TABS, routeLabels, type ArsenalTab } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';

	const TAB_META: Record<ArsenalTab, { label: string; icon: IconComponent; panel: Component }> = {
		nuclei: { label: 'Nuclei', icon: ShieldAlertIcon, panel: NucleiLibrary },
		wordlists: { label: 'Wordlists', icon: WholeWordIcon, panel: WordlistLibrary }
	};

	const DEFAULT_TAB = ARSENAL_TABS[0];
	const validTabs = new Set<string>(ARSENAL_TABS);

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<ArsenalTab>(
		validTabs.has(initialTab) ? (initialTab as ArsenalTab) : DEFAULT_TAB
	);

	$effect(() => {
		const tab = activeTab;
		if (!browser) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (tab === DEFAULT_TAB) params.delete('tab');
		else params.set('tab', tab);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.arsenal}</h1>
		<p class="mt-1 text-sm text-muted-foreground">
			Scanners, checks and wordlists available to scan engines
		</p>
	</div>

	<Tabs.Root
		value={activeTab}
		onValueChange={(v) => {
			if (v) activeTab = v as ArsenalTab;
		}}
	>
		<Tabs.List class="w-full sm:w-fit">
			{#each ARSENAL_TABS as tab (tab)}
				{@const Icon = TAB_META[tab].icon}
				<Tabs.Trigger value={tab} class="gap-1.5">
					<Icon class="size-4" />
					{TAB_META[tab].label}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		{#each ARSENAL_TABS as tab (tab)}
			{@const Panel = TAB_META[tab].panel}
			<Tabs.Content value={tab} class="mt-6">
				<Panel />
			</Tabs.Content>
		{/each}
	</Tabs.Root>
</div>
