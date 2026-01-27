<script lang="ts" module>
	import LayoutDashboardIcon from '@lucide/svelte/icons/layout-dashboard';
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import ZapIcon from '@lucide/svelte/icons/zap';
	import ShieldAlertIcon from '@lucide/svelte/icons/shield-alert';
	import DatabaseIcon from '@lucide/svelte/icons/database';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
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
						title: 'Scans',
						url: '/scans',
						icon: RadarIcon
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
					}
				]
			},
			{
				label: 'Intelligence',
				items: [
					{
						title: 'Vulnerabilities',
						url: '/vulnerabilities',
						icon: ShieldAlertIcon
					},
					{
						title: 'Assets',
						url: '/assets',
						icon: DatabaseIcon,
						items: [
							{
								title: 'Subdomains',
								url: '/assets/subdomains'
							},
							{
								title: 'Endpoints',
								url: '/assets/endpoints'
							},
							{
								title: 'IP Addresses',
								url: '/assets/ips'
							},
							{
								title: 'Technologies',
								url: '/assets/technologies'
							}
						]
					}
				]
			},
			{
				label: 'Reporting',
				items: [
					{
						title: 'Reports',
						url: '/reports',
						icon: FileTextIcon
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
