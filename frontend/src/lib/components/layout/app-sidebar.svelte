<script lang="ts">
	import LayoutDashboardIcon from '@lucide/svelte/icons/layout-dashboard';
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import CalendarClockIcon from '@lucide/svelte/icons/calendar-clock';
	import CogIcon from '@lucide/svelte/icons/cog';
	import LayersIcon from '@lucide/svelte/icons/layers';
	import SwordsIcon from '@lucide/svelte/icons/swords';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import NetworkIcon from '@lucide/svelte/icons/network';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import NavMain, { type NavGroup } from './nav-main.svelte';
	import NavUser from './nav-user.svelte';
	import ProjectSwitcher from './project-switcher.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import type { ComponentProps } from 'svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { reports } from '$lib/stores/reports.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';

	let {
		ref = $bindable(null),
		collapsible = 'icon',
		...restProps
	}: ComponentProps<typeof Sidebar.Root> = $props();

	const userData = $derived({
		name: auth.user?.username ?? 'Unknown user',
		email: auth.user?.email ?? 'admin@rengine.local',
		is_superuser: auth.user?.is_superuser ?? false
	});

	const navGroups = $derived<NavGroup[]>([
		{
			label: null,
			items: [{ title: routeLabels.dashboard, url: ROUTES.dashboard, icon: LayoutDashboardIcon }]
		},
		{
			label: 'Attack surface',
			items: [
				{ title: routeLabels.targets, url: ROUTES.targets, icon: CrosshairIcon },
				{
					title: routeLabels.scans,
					url: ROUTES.scans,
					icon: RadarIcon,
					badge: liveScans.hasLive ? { count: liveScans.count, live: true } : null
				},
				{ title: routeLabels.schedules, url: ROUTES.schedules, icon: CalendarClockIcon }
			]
		},
		{
			label: routeLabels.automation,
			items: [
				{ title: routeLabels.engines, url: ROUTES.engines, icon: CogIcon },
				{ title: routeLabels.contexts, url: ROUTES.contexts, icon: LayersIcon }
			]
		},
		{
			label: null,
			items: [
				{
					title: routeLabels.reports,
					url: ROUTES.reports(),
					icon: FileTextIcon,
					badge: reports.liveCount ? { count: reports.liveCount, live: true } : null
				},
				{ title: routeLabels.arsenal, url: ROUTES.arsenal(), icon: SwordsIcon },
				{ title: routeLabels.ai, url: ROUTES.ai(), icon: SparklesIcon },
				{ title: routeLabels.mcp, url: ROUTES.mcp(), icon: NetworkIcon }
			]
		},
		{
			label: null,
			items: [{ title: routeLabels.settings, url: ROUTES.settings(), icon: Settings2Icon }]
		}
	]);
</script>

<Sidebar.Root bind:ref {collapsible} variant="inset" {...restProps}>
	<Sidebar.Header>
		<ProjectSwitcher />
	</Sidebar.Header>
	<Sidebar.Content>
		<NavMain groups={navGroups} />
	</Sidebar.Content>
	<Sidebar.Footer>
		<NavUser user={userData} />
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
