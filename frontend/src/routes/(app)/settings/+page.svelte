<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack, type Component } from 'svelte';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import ApiKeysTab from '$lib/components/settings/api-keys-tab.svelte';
	import InstanceSettingsTab from '$lib/components/settings/instance-settings-tab.svelte';
	import ProxiesTab from '$lib/components/settings/proxies-tab.svelte';
	import NotificationChannelsTab from '$lib/components/settings/notification-channels-tab.svelte';
	import SlidersHorizontalIcon from '@lucide/svelte/icons/sliders-horizontal';
	import KeyIcon from '@lucide/svelte/icons/key-round';
	import RouteIcon from '@lucide/svelte/icons/route';
	import BellIcon from '@lucide/svelte/icons/bell';
	import { SETTINGS_TABS, type SettingsTab } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';

	const TAB_META: Record<SettingsTab, { label: string; icon: IconComponent; panel: Component }> = {
		general: { label: 'General', icon: SlidersHorizontalIcon, panel: InstanceSettingsTab },
		'api-keys': { label: 'API Keys', icon: KeyIcon, panel: ApiKeysTab },
		proxies: { label: 'Proxies', icon: RouteIcon, panel: ProxiesTab },
		notifications: { label: 'Notifications', icon: BellIcon, panel: NotificationChannelsTab }
	};

	const DEFAULT_TAB = SETTINGS_TABS[0];
	const validTabs = new Set<string>(SETTINGS_TABS);

	const initialTab = page.url.searchParams.get('tab') ?? DEFAULT_TAB;
	let activeTab = $state<SettingsTab>(
		validTabs.has(initialTab) ? (initialTab as SettingsTab) : DEFAULT_TAB
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
		<h1 class="text-2xl font-semibold tracking-tight">Settings</h1>
		<p class="text-sm text-muted-foreground mt-1">Instance-wide configuration</p>
	</div>

	<Tabs.Root
		value={activeTab}
		onValueChange={(v) => {
			if (v) activeTab = v as SettingsTab;
		}}
	>
		<Tabs.List class="w-full sm:w-fit">
			{#each SETTINGS_TABS as tab (tab)}
				{@const Icon = TAB_META[tab].icon}
				<Tabs.Trigger value={tab} class="gap-1.5">
					<Icon class="size-4" />
					<span class="hidden sm:inline">{TAB_META[tab].label}</span>
				</Tabs.Trigger>
			{/each}
		</Tabs.List>

		{#each SETTINGS_TABS as tab (tab)}
			{@const Panel = TAB_META[tab].panel}
			<Tabs.Content value={tab} class="mt-6">
				<Panel />
			</Tabs.Content>
		{/each}
	</Tabs.Root>
</div>
