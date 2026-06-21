<script lang="ts" module>
	import LayoutDashboardIcon from '@lucide/svelte/icons/layout-dashboard';
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import ZapIcon from '@lucide/svelte/icons/zap';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';

	const data = {
		navGroups: [
			{
				label: null,
				items: [
					{
						title: 'Dashboard',
						url: '/dashboard',
						icon: LayoutDashboardIcon
					}
				]
			},
			{
				label: 'Reconnaissance',
				items: [
					{
						title: 'Targets',
						url: '/targets',
						icon: CrosshairIcon
					},
					{
						title: 'Automation',
						url: '/automation',
						icon: ZapIcon,
						items: [
							{
								title: 'Scans',
								url: '/automation/scans'
							},
							{
								title: 'Scan Engines',
								url: '/automation/engines'
							},
							{
								title: 'Scan Contexts',
								url: '/automation/contexts'
							}
						]
					}
				]
			},
			{
				label: null,
				items: [
					{
						title: 'Settings',
						url: '/settings',
						icon: Settings2Icon
					}
				]
			}
		]
	};
</script>

<script lang="ts">
	import NavMain from './nav-main.svelte';
	import NavUser from './nav-user.svelte';
	import ProjectSwitcher from './project-switcher.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import type { ComponentProps } from 'svelte';

	import { auth } from '$lib/stores/auth.svelte';

	let {
		ref = $bindable(null),
		collapsible = 'icon',
		...restProps
	}: ComponentProps<typeof Sidebar.Root> = $props();

	const userData = $derived({
		name: auth.user?.username ?? 'Unknown User',
		email: auth.user?.email ?? 'admin@rengine.local',
		is_superuser: auth.user?.is_superuser ?? false
	});
</script>

<Sidebar.Root {collapsible} variant="inset" {...restProps}>
	<Sidebar.Header>
		<ProjectSwitcher />
	</Sidebar.Header>
	<Sidebar.Content>
		<NavMain groups={data.navGroups} />
	</Sidebar.Content>
	<Sidebar.Footer>
		<NavUser user={userData} />
	</Sidebar.Footer>
</Sidebar.Root>
