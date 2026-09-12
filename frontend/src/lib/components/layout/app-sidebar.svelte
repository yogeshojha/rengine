<script lang="ts">
	import LayoutDashboardIcon from '@lucide/svelte/icons/layout-dashboard';
	import TargetIcon from '@lucide/svelte/icons/target';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import StickyNoteIcon from '@lucide/svelte/icons/sticky-note';
	import WorkflowIcon from '@lucide/svelte/icons/workflow';
	import LibraryIcon from '@lucide/svelte/icons/library';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import ScanEyeIcon from '@lucide/svelte/icons/scan-eye';
	import CableIcon from '@lucide/svelte/icons/cable';
	import AwardIcon from '@lucide/svelte/icons/award';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import NavMain, { type NavGroup } from './nav-main.svelte';
	import { SURFACE_ORDER } from '$lib/config/surface';
	import { surfaceStore } from '$lib/stores/surface.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { compactCount } from '$lib/utilities/strings';
	import NavUser from './nav-user.svelte';
	import ProjectSwitcher from './project-switcher.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import type { ComponentProps } from 'svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { reports } from '$lib/stores/reports.svelte';
	import { ROUTES, routeLabels, SETTINGS_SECTIONS } from '$lib/config/routes';
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

	const settingsSections = $derived(
		SETTINGS_SECTIONS.filter(
			(section) => section !== 'bounty-hub' || capabilitiesStore.has(Capability.BOUNTY_PROGRAMS)
		).map((section) => ({ title: routeLabels[section], url: ROUTES.settings(section) }))
	);

	const navGroups = $derived<NavGroup[]>([
		{
			label: null,
			items: [{ title: routeLabels.dashboard, url: ROUTES.dashboard, icon: LayoutDashboardIcon }]
		},
		{
			label: routeLabels.surface,
			items: [
				...surfaceItems,
				{
					title: routeLabels.exposures,
					url: ROUTES.exposures(),
					icon: ScanEyeIcon,
					badge: surfaceStore.exposures
						? { label: compactCount(surfaceStore.exposures), tone: 'muted' as const }
						: null
				}
			]
		},
		{
			label: 'Discovery',
			items: [
				...(capabilitiesStore.has(Capability.BOUNTY_PROGRAMS)
					? [{ title: routeLabels['bounty-hub'], url: ROUTES.bountyHub(), icon: AwardIcon }]
					: []),
				{ title: routeLabels.targets, url: ROUTES.targets, icon: TargetIcon },
				{
					title: routeLabels.scans,
					url: ROUTES.scans,
					icon: RadarIcon,
					badge: liveScans.hasLive
						? { label: String(liveScans.count), live: true, tone: 'info' as const }
						: null
				},
				{ title: routeLabels.connectors, url: ROUTES.connectors(), icon: CableIcon },
				{ title: routeLabels.notes, url: ROUTES.notes, icon: StickyNoteIcon }
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
				{ title: routeLabels.arsenal, url: ROUTES.arsenal(), icon: LibraryIcon },
				{
					title: routeLabels.automation,
					url: ROUTES.automation,
					icon: WorkflowIcon,
					items: [
						{ title: routeLabels.engines, url: ROUTES.engines },
						{ title: routeLabels.contexts, url: ROUTES.contexts },
						{ title: routeLabels.schedules, url: ROUTES.schedules }
					]
				}
			]
		}
	]);

	const settingsGroup = $derived<NavGroup[]>([
		{
			label: null,
			items: [
				{
					title: routeLabels.settings,
					url: ROUTES.settings(),
					icon: Settings2Icon,
					items: settingsSections
				}
			]
		}
	]);
</script>

<Sidebar.Root bind:ref {collapsible} variant="inset" {...restProps}>
	<Sidebar.Header>
		<ProjectSwitcher />
	</Sidebar.Header>
	<Sidebar.Content class="overflow-hidden">
		<ScrollArea class="min-h-0 flex-1">
			<NavMain groups={navGroups} />
		</ScrollArea>
	</Sidebar.Content>
	<Sidebar.Footer class="border-t border-sidebar-border">
		<NavMain groups={settingsGroup} class="p-0" />
		<NavUser user={userData} />
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
