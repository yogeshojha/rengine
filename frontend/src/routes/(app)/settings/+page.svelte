<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import ApiKeysTab from '$lib/components/settings/api-keys-tab.svelte';
	import InstanceSettingsTab from '$lib/components/settings/instance-settings-tab.svelte';
	import ProxiesTab from '$lib/components/settings/proxies-tab.svelte';
	import NotificationChannelsTab from '$lib/components/settings/notification-channels-tab.svelte';
	import SlidersHorizontalIcon from '@lucide/svelte/icons/sliders-horizontal';
	import KeyIcon from '@lucide/svelte/icons/key-round';
	import RouteIcon from '@lucide/svelte/icons/route';
	import BellIcon from '@lucide/svelte/icons/bell';

	const validTabs = new Set(['general', 'api-keys', 'proxies', 'notifications']);

	const initialTab = page.url.searchParams.get('tab') ?? 'general';
	let activeTab = $state(validTabs.has(initialTab) ? initialTab : 'general');

	$effect(() => {
		const tab = activeTab;
		if (!browser) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (tab === 'general') params.delete('tab');
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
		<p class="text-sm text-muted-foreground mt-1">Manage your reNgine instance configuration</p>
	</div>

	<Tabs.Root value={activeTab} onValueChange={(v) => { if (v) activeTab = v; }}>
		<Tabs.List class="w-full sm:w-fit">
			<Tabs.Trigger value="general" class="gap-1.5">
				<SlidersHorizontalIcon class="size-4" />
				<span class="hidden sm:inline">General</span>
			</Tabs.Trigger>
			<Tabs.Trigger value="api-keys" class="gap-1.5">
				<KeyIcon class="size-4" />
				<span class="hidden sm:inline">API Keys</span>
			</Tabs.Trigger>
			<Tabs.Trigger value="proxies" class="gap-1.5">
				<RouteIcon class="size-4" />
				<span class="hidden sm:inline">Proxies</span>
			</Tabs.Trigger>
			<Tabs.Trigger value="notifications" class="gap-1.5">
				<BellIcon class="size-4" />
				<span class="hidden sm:inline">Notifications</span>
			</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content value="general" class="mt-6">
			<InstanceSettingsTab />
		</Tabs.Content>

		<Tabs.Content value="api-keys" class="mt-6">
			<ApiKeysTab />
		</Tabs.Content>

		<Tabs.Content value="proxies" class="mt-6">
			<ProxiesTab />
		</Tabs.Content>

		<Tabs.Content value="notifications" class="mt-6">
			<NotificationChannelsTab />
		</Tabs.Content>
	</Tabs.Root>
</div>
