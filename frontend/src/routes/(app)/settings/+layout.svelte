<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import RouteIcon from '@lucide/svelte/icons/route';
	import BellIcon from '@lucide/svelte/icons/bell';
	import AwardIcon from '@lucide/svelte/icons/award';
	import CpuIcon from '@lucide/svelte/icons/cpu';
	import BotIcon from '@lucide/svelte/icons/bot';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { ROUTES, routeLabels, SETTINGS_SECTIONS, type SettingsSection } from '$lib/config/routes';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { Capability } from '$lib/config/capabilities';
	import type { IconComponent } from '$lib/config/icons';

	let { children } = $props();

	const ICONS: Record<SettingsSection, IconComponent> = {
		general: Settings2Icon,
		'api-keys': KeyRoundIcon,
		proxies: RouteIcon,
		notifications: BellIcon,
		'bounty-hub': AwardIcon,
		ai: CpuIcon,
		mcp: BotIcon
	};

	const sections = $derived(
		SETTINGS_SECTIONS.filter(
			(section) => section !== 'bounty-hub' || capabilitiesStore.has(Capability.BOUNTY_PROGRAMS)
		)
	);
	const active = $derived(
		sections.find((section) => page.url.pathname.startsWith(ROUTES.settings(section))) ?? ''
	);
</script>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.settings}</h1>
		<p class="mt-1 text-sm text-muted-foreground">Instance-wide configuration</p>
	</div>

	<Tabs.Root
		value={active}
		onValueChange={(v) => {
			if (v && v !== active) goto(ROUTES.settings(v as SettingsSection));
		}}
	>
		<ScrollArea orientation="horizontal" class="w-full sm:w-fit">
			<Tabs.List>
				{#each sections as section (section)}
					{@const Icon = ICONS[section]}
					<Tabs.Trigger value={section} class="gap-1.5">
						<Icon class="size-4" />
						{routeLabels[section]}
					</Tabs.Trigger>
				{/each}
			</Tabs.List>
		</ScrollArea>
	</Tabs.Root>

	{@render children()}
</div>
