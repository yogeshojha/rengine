<script lang="ts">
	import LayoutDashboardIcon from '@lucide/svelte/icons/layout-dashboard';
	import TargetIcon from '@lucide/svelte/icons/target';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import StickyNoteIcon from '@lucide/svelte/icons/sticky-note';
	import ZapIcon from '@lucide/svelte/icons/zap';
	import NewspaperIcon from '@lucide/svelte/icons/newspaper';
	import LayersIcon from '@lucide/svelte/icons/layers';
	import WorkflowIcon from '@lucide/svelte/icons/workflow';
	import CalendarClockIcon from '@lucide/svelte/icons/calendar-clock';
	import NinjaIcon from '$lib/components/icons/ninja.svelte';
	import LibraryIcon from '@lucide/svelte/icons/library';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import ScanEyeIcon from '@lucide/svelte/icons/scan-eye';
	import Share2Icon from '@lucide/svelte/icons/share-2';
	import CableIcon from '@lucide/svelte/icons/cable';
	import SquareKanbanIcon from '@lucide/svelte/icons/square-kanban';
	import MessageSquareIcon from '@lucide/svelte/icons/message-square';
	import BotIcon from '@lucide/svelte/icons/bot';
	import Settings2Icon from '@lucide/svelte/icons/settings-2';
	import NavMain, { type NavGroup } from './nav-main.svelte';
	import { ASSET_DIMENSIONS, FINDINGS_ROOT, SURFACE } from '$lib/config/surface';
	import NavUser from './nav-user.svelte';
	import ProjectSwitcher from './project-switcher.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import { untrack, type ComponentProps } from 'svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { reports } from '$lib/stores/reports.svelte';
	import { whatsNewStore } from '$lib/stores/whats-new.svelte';
	import { FINDINGS_PATHS, ROUTES, routeLabels } from '$lib/config/routes';
	import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
	import { Capability } from '$lib/config/capabilities';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';

	let {
		ref = $bindable(null),
		collapsible = 'icon',
		...restProps
	}: ComponentProps<typeof Sidebar.Root> = $props();

	const assetItems = $derived(
		ASSET_DIMENSIONS.map((spec) => ({ title: spec.label, url: ROUTES.surface(spec.tab) }))
	);
	const findings = SURFACE[FINDINGS_ROOT];
	const compact = (n: number) =>
		new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 })
			.format(n)
			.toLowerCase();

	$effect(() => {
		const id = projectsStore.activeProject?.id;
		if (id) untrack(() => void whatsNewStore.fetch(id));
	});

	const bountyOn = $derived(capabilitiesStore.has(Capability.BOUNTY_PROGRAMS));
	$effect(() => {
		if (bountyOn) untrack(() => void bountyVocabulary.load());
	});
	const reportPlatforms = $derived(bountyVocabulary.platforms.filter((p) => p.tracks_reports));

	const userData = $derived({
		name: auth.user?.username ?? 'Unknown user',
		email: auth.user?.email ?? 'admin@rengine.local',
		is_superuser: auth.user?.is_superuser ?? false
	});

	const navGroups = $derived<NavGroup[]>([
		{
			label: null,
			items: [
				{ title: routeLabels.dashboard, url: ROUTES.dashboard, icon: LayoutDashboardIcon },
				{ title: routeLabels.targets, url: ROUTES.targets, icon: TargetIcon },
				{
					title: routeLabels['whats-new'],
					url: ROUTES.whatsNew(),
					icon: NewspaperIcon,
					badge: whatsNewStore.unseen
						? { label: compact(whatsNewStore.unseen), tone: 'info' as const }
						: null
				},
				{ title: routeLabels.tripwires, url: ROUTES.tripwires(), icon: ZapIcon },
				{ title: routeLabels.notes, url: ROUTES.notes, icon: StickyNoteIcon }
			]
		},
		{
			label: routeLabels.surface,
			items: [
				{
					title: routeLabels.assets,
					url: ROUTES.surface(ASSET_DIMENSIONS[0].tab),
					icon: LayersIcon,
					items: assetItems
				},
				{
					title: findings.label,
					url: ROUTES.surface(findings.tab),
					icon: findings.icon,
					match: FINDINGS_PATHS
				},
				{ title: routeLabels.exposures, url: ROUTES.exposures(), icon: ScanEyeIcon },
				{ title: routeLabels.correlation, url: ROUTES.correlation, icon: Share2Icon }
			]
		},
		{
			label: routeLabels.scans,
			items: [
				{
					title: routeLabels.scans,
					url: ROUTES.scans,
					icon: RadarIcon,
					badge: liveScans.running
						? { label: String(liveScans.running), live: true, tone: 'info' as const }
						: null
				},
				{ title: routeLabels.schedules, url: ROUTES.schedules, icon: CalendarClockIcon },
				{
					title: routeLabels.engineSetup,
					url: ROUTES.engines,
					icon: WorkflowIcon,
					items: [
						{ title: routeLabels.engines, url: ROUTES.engines },
						{ title: routeLabels.contexts, url: ROUTES.contexts }
					]
				}
			]
		},
		...(bountyOn
			? [
					{
						label: routeLabels.bounty,
						items: [
							{
								title: routeLabels['bounty-hub'],
								url: ROUTES.bountyHub(),
								icon: NinjaIcon,
								items: reportPlatforms.length
									? [
											{ title: routeLabels.programs, url: ROUTES.bountyHub(), exact: true },
											...reportPlatforms.map((p) => ({
												title: p.label,
												url: ROUTES.bountyReports(p.key)
											}))
										]
									: undefined
							}
						]
					}
				]
			: []),
		{
			label: routeLabels.arsenal,
			items: [{ title: routeLabels.arsenal, url: ROUTES.arsenal(), icon: LibraryIcon }]
		},
		{
			label: routeLabels.reporting,
			items: [
				{
					title: routeLabels.reports,
					url: ROUTES.reports(),
					icon: FileTextIcon,
					badge: reports.liveCount
						? { label: String(reports.liveCount), live: true, tone: 'info' as const }
						: null
				}
			]
		},
		{
			label: routeLabels.integrations,
			items: [
				{ title: routeLabels.connectors, url: ROUTES.connectors(), icon: CableIcon },
				{
					title: routeLabels['issue-trackers'],
					url: ROUTES.issueTrackers(),
					icon: SquareKanbanIcon
				},
				{
					title: routeLabels['remote-control'],
					url: ROUTES.remoteControl(),
					icon: MessageSquareIcon
				},
				{ title: routeLabels.agents, url: ROUTES.agents(), icon: BotIcon }
			]
		}
	]);

	const settingsGroup = $derived<NavGroup[]>([
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
