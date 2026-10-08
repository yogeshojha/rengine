<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import RouteIcon from '@lucide/svelte/icons/route';
	import BellIcon from '@lucide/svelte/icons/bell';
	import CpuIcon from '@lucide/svelte/icons/cpu';
	import UsersIcon from '@lucide/svelte/icons/users';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import PageHeader from '$lib/components/page-header.svelte';
	import {
		ADMIN_SETTINGS,
		ROUTES,
		routeLabels,
		SETTINGS_SECTIONS,
		type SettingsSection
	} from '$lib/config/routes';
	import { auth } from '$lib/stores/auth.svelte';
	import { settingsActions } from '$lib/stores/settings-actions.svelte';
	import type { IconComponent } from '$lib/config/icons';

	let { children } = $props();

	const ICONS: Record<SettingsSection, IconComponent> = {
		general: Settings2Icon,
		'api-keys': KeyRoundIcon,
		proxies: RouteIcon,
		notifications: BellIcon,
		ai: CpuIcon,
		users: UsersIcon
	};

	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const sections = $derived(
		SETTINGS_SECTIONS.filter((section) => isAdmin || !ADMIN_SETTINGS.includes(section))
	);
	const active = $derived(
		sections.find((section) => page.url.pathname.startsWith(ROUTES.settings(section))) ?? ''
	);
</script>

<div class="flex w-full max-w-5xl flex-col gap-6">
	<PageHeader title={routeLabels.settings} description="Instance-wide configuration" />

	<div class="flex flex-wrap items-center justify-between gap-3 border-b">
		<Tabs.Root
			value={active}
			onValueChange={(v) => {
				if (v && v !== active) goto(ROUTES.settings(v as SettingsSection));
			}}
			class="min-w-0 self-end"
		>
			<ScrollArea orientation="horizontal" class="w-full sm:w-fit">
				<Tabs.List variant="line" class="h-10 w-max justify-start">
					{#each sections as section (section)}
						{@const Icon = ICONS[section]}
						<Tabs.Trigger value={section} class="flex-none px-3">
							<Icon class="size-4" />
							{routeLabels[section]}
						</Tabs.Trigger>
					{/each}
				</Tabs.List>
			</ScrollArea>
		</Tabs.Root>
		{#if settingsActions.snippet}
			<div class="flex items-center gap-2">{@render settingsActions.snippet()}</div>
		{/if}
	</div>

	{@render children()}
</div>
