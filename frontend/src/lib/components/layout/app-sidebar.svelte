<script lang="ts" module>
	import LayoutDashboardIcon from '@lucide/svelte/icons/layout-dashboard';
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import ZapIcon from '@lucide/svelte/icons/zap';
	import ClockIcon from '@lucide/svelte/icons/clock';
	import ShieldAlertIcon from '@lucide/svelte/icons/shield-alert';
	import DatabaseIcon from '@lucide/svelte/icons/database';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';

	const data = {
		navMain: [
			{
				title: 'Dashboard',
				url: '/dashboard',
				icon: LayoutDashboardIcon,
				isActive: true
			},
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
						title: 'Scan Engines',
						url: '/automation/engines'
					},
					{
						title: 'Scan Contexts',
						url: '/automation/contexts'
					}
				]
			},
			{
				title: 'Scans',
				url: '/scans',
				icon: ClockIcon
			},
			{
				title: 'Vulnerabilities',
				url: '/vulnerabilities',
				icon: ShieldAlertIcon
			},
			{
				title: 'Assets',
				url: '/assets',
				icon: DatabaseIcon
			},
			{
				title: 'Reports',
				url: '/reports',
				icon: FileTextIcon
			},
			{
				title: 'Settings',
				url: '/settings',
				icon: Settings2Icon
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
	})
</script>

<Sidebar.Root {collapsible} {...restProps}>
	<Sidebar.Header>
		<ProjectSwitcher />
	</Sidebar.Header>
	<Sidebar.Content>
		<NavMain items={data.navMain} />
	</Sidebar.Content>
	<Sidebar.Footer>
		<NavUser user={userData} />
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
