<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack, type Component } from 'svelte';
	import ListFilterIcon from '@lucide/svelte/icons/list-filter';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import RulesPanel from '$lib/components/interest/rules-panel.svelte';
	import DismissedPanel from '$lib/components/interest/dismissed-panel.svelte';
	import { INTEREST_TABS, routeLabels, type InterestTab } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';

	const TAB_META: Record<InterestTab, { label: string; icon: IconComponent; panel: Component }> = {
		rules: { label: 'Rules', icon: ListFilterIcon, panel: RulesPanel },
		dismissed: { label: 'Dismissed', icon: EyeOffIcon, panel: DismissedPanel }
	};

	const DEFAULT_TAB = INTEREST_TABS[0];
	const validTabs = new Set<string>(INTEREST_TABS);

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<InterestTab>(
		validTabs.has(initialTab) ? (initialTab as InterestTab) : DEFAULT_TAB
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
		<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.interest}</h1>
		<p class="mt-1 text-sm text-muted-foreground">
			What makes an asset worth opening first, and what you have told reNgine to stop showing you.
		</p>
	</div>

	<Tabs.Root
		value={activeTab}
		onValueChange={(v) => {
			if (v) activeTab = v as InterestTab;
		}}
	>
		<Tabs.List class="w-full sm:w-fit">
			{#each INTEREST_TABS as tab (tab)}
				{@const Icon = TAB_META[tab].icon}
				<Tabs.Trigger value={tab} class="gap-1.5">
					<Icon class="size-4" />
					{TAB_META[tab].label}
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		{#each INTEREST_TABS as tab (tab)}
			{@const Panel = TAB_META[tab].panel}
			<Tabs.Content value={tab} class="mt-6">
				<Panel />
			</Tabs.Content>
		{/each}
	</Tabs.Root>
</div>
