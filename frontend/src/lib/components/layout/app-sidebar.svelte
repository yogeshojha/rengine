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
	import SparkleIcon from '@lucide/svelte/icons/sparkle';
	import NetworkIcon from '@lucide/svelte/icons/network';
	import PlugZapIcon from '@lucide/svelte/icons/plug-zap';
	import TargetIcon from '@lucide/svelte/icons/target';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import NavMain, { type NavGroup } from './nav-main.svelte';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import { surfaceStore } from '$lib/stores/surface.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { compactCount } from '$lib/utilities/strings';
	import NavUser from './nav-user.svelte';
	import ProjectSwitcher from './project-switcher.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import type { ComponentProps } from 'svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { reports } from '$lib/stores/reports.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { Capability } from '$lib/config/capabilities';

	let {
		ref = $bindable(null),
		collapsible = 'icon',
		...restProps
	}: ComponentProps<typeof Sidebar.Root> = $props();

	$effect(() => {
		const id = projectsStore.activeProject?.id;
		if (id) void surfaceStore.load(id);
	});

	const surfaceItems = $derived(
		SURFACE_ORDER.map((spec) => {
			const total = surfaceStore.total(spec.key);
			return {
				title: spec.label,
				url: ROUTES.surface(spec.tab),
				icon: spec.icon,
				badge: total ? { label: compactCount(total), tone: 'muted' as const } : null
			};
		})
	);

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
			label: routeLabels.surface,
			items: surfaceItems
		},
		{
			label: 'Reconnaissance',
			items: [
				{ title: routeLabels.targets, url: ROUTES.targets, icon: CrosshairIcon },
				{
					title: routeLabels.scans,
					url: ROUTES.scans,
					icon: RadarIcon,
					badge: liveScans.hasLive
						? { label: String(liveScans.count), live: true, tone: 'info' as const }
						: null
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
					badge: reports.liveCount
						? { label: String(reports.liveCount), live: true, tone: 'info' as const }
						: null
				},
				{ title: routeLabels.interest, url: ROUTES.interest(), icon: SparkleIcon },
				{ title: routeLabels.arsenal, url: ROUTES.arsenal(), icon: SwordsIcon },
				...(capabilitiesStore.has(Capability.BOUNTY_PROGRAMS)
					? [{ title: routeLabels.bountyHub, url: ROUTES.bountyHub(), icon: TargetIcon }]
					: []),
				{ title: routeLabels.ai, url: ROUTES.ai(), icon: SparklesIcon },
				{ title: routeLabels.mcp, url: ROUTES.mcp(), icon: NetworkIcon },
				{ title: routeLabels.connectors, url: ROUTES.connectors(), icon: PlugZapIcon }
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
