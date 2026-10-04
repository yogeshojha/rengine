import LayoutDashboardIcon from '@lucide/svelte/icons/layout-dashboard';
import TargetIcon from '@lucide/svelte/icons/target';
import RadarIcon from '@lucide/svelte/icons/radar';
import StickyNoteIcon from '@lucide/svelte/icons/sticky-note';
import ZapIcon from '@lucide/svelte/icons/zap';
import NewspaperIcon from '@lucide/svelte/icons/newspaper';
import LayersIcon from '@lucide/svelte/icons/layers';
import WorkflowIcon from '@lucide/svelte/icons/workflow';
import NinjaIcon from '$lib/components/icons/ninja.svelte';
import LibraryIcon from '@lucide/svelte/icons/library';
import FileTextIcon from '@lucide/svelte/icons/file-text';
import ScanEyeIcon from '@lucide/svelte/icons/scan-eye';
import PlugIcon from '@lucide/svelte/icons/plug';
import Settings2Icon from '@lucide/svelte/icons/settings-2';
import type { NavGroup, NavItem } from './nav-main.svelte';
import { ASSET_DIMENSIONS, FINDINGS_ROOT, SURFACE } from '$lib/config/surface';
import { FINDINGS_PATHS, ROUTES, routeLabels } from '$lib/config/routes';
import { Capability } from '$lib/config/capabilities';
import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
import { liveScans } from '$lib/stores/live-scans.svelte';
import { projectsStore } from '$lib/stores/projects.svelte';
import { reports } from '$lib/stores/reports.svelte';
import { whatsNewStore } from '$lib/stores/whats-new.svelte';
import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
import { sidebarLayout } from '$lib/stores/sidebar-layout.svelte';
import { compactCount, COMPACT_FROM_SHORT } from '$lib/utilities/numbers';

export const LOCKED_NAV_ITEMS: readonly string[] = ['dashboard', 'settings'];

function visible(groups: NavGroup[]): NavGroup[] {
	const out: NavGroup[] = [];
	for (const group of groups) {
		const items: NavItem[] = [];
		for (const item of group.items) {
			if (sidebarLayout.hidden(item.id)) continue;
			if (!item.items) {
				items.push(item);
				continue;
			}
			const children = item.items.filter((c) => !sidebarLayout.hidden(c.id));
			if (children.length) items.push({ ...item, items: children });
		}
		if (items.length) out.push({ ...group, items });
	}
	return out;
}

export function useSidebarNav() {
	const bountyOn = $derived(capabilitiesStore.has(Capability.BOUNTY_PROGRAMS));
	const reportPlatforms = $derived(bountyVocabulary.platforms.filter((p) => p.tracks_reports));
	const findings = SURFACE[FINDINGS_ROOT];
	const liveReports = $derived(
		reports.rowsProjectId === projectsStore.activeProject?.id ? reports.liveCount : 0
	);

	const main = $derived<NavGroup[]>([
		{
			label: null,
			items: [
				{
					id: 'dashboard',
					title: routeLabels.dashboard,
					url: ROUTES.dashboard,
					icon: LayoutDashboardIcon
				},
				{
					id: 'whats-new',
					title: routeLabels['whats-new'],
					url: ROUTES.whatsNew(),
					icon: NewspaperIcon,
					badge: whatsNewStore.unseen
						? { label: compactCount(whatsNewStore.unseen, COMPACT_FROM_SHORT) }
						: null
				},
				{ id: 'targets', title: routeLabels.targets, url: ROUTES.targets, icon: TargetIcon },
				{ id: 'notes', title: routeLabels.notes, url: ROUTES.notes, icon: StickyNoteIcon }
			]
		},
		{
			label: routeLabels.surface,
			items: [
				{
					id: 'assets',
					title: routeLabels.assets,
					url: ROUTES.surface(ASSET_DIMENSIONS[0].tab),
					icon: LayersIcon,
					items: ASSET_DIMENSIONS.map((spec) => ({
						id: `assets:${spec.tab}`,
						title: spec.label,
						url: ROUTES.surface(spec.tab)
					}))
				},
				{
					id: 'findings',
					title: findings.label,
					url: ROUTES.surface(findings.tab),
					icon: findings.icon,
					match: FINDINGS_PATHS
				},
				{
					id: 'exposures',
					title: routeLabels.exposures,
					url: ROUTES.exposures(),
					icon: ScanEyeIcon
				}
			]
		},
		{
			label: routeLabels.operations,
			items: [
				{
					id: 'scans',
					title: routeLabels.scans,
					url: ROUTES.scans,
					icon: RadarIcon,
					badge: liveScans.running ? { label: String(liveScans.running), live: true } : null
				},
				{
					id: 'scan-setup',
					title: routeLabels.engineSetup,
					url: ROUTES.engines,
					icon: WorkflowIcon,
					items: [
						{ id: 'engines', title: routeLabels.engines, url: ROUTES.engines },
						{ id: 'contexts', title: routeLabels.contexts, url: ROUTES.contexts },
						{ id: 'schedules', title: routeLabels.schedules, url: ROUTES.schedules }
					]
				},
				{ id: 'tripwires', title: routeLabels.tripwires, url: ROUTES.tripwires(), icon: ZapIcon },
				{
					id: 'reports',
					title: routeLabels.reports,
					url: ROUTES.reports(),
					icon: FileTextIcon,
					badge: liveReports ? { label: String(liveReports), live: true } : null
				},
				...(bountyOn
					? [
							{
								id: 'bounty-hub',
								title: routeLabels['bounty-hub'],
								url: ROUTES.bountyHub(),
								icon: NinjaIcon,
								items: reportPlatforms.length
									? [
											{
												id: 'bounty-hub:programs',
												title: routeLabels.programs,
												url: ROUTES.bountyHub(),
												exact: true
											},
											...reportPlatforms.map((p) => ({
												id: `bounty-hub:${p.key}`,
												title: p.label,
												url: ROUTES.bountyReports(p.key)
											}))
										]
									: undefined
							}
						]
					: [])
			]
		}
	]);

	const footer = $derived<NavGroup[]>([
		{
			label: null,
			items: [
				{ id: 'arsenal', title: routeLabels.arsenal, url: ROUTES.arsenal(), icon: LibraryIcon },
				{
					id: 'integrations',
					title: routeLabels.integrations,
					url: ROUTES.connectors(),
					icon: PlugIcon,
					items: [
						{ id: 'connectors', title: routeLabels.connectors, url: ROUTES.connectors() },
						{
							id: 'issue-trackers',
							title: routeLabels['issue-trackers'],
							url: ROUTES.issueTrackers()
						},
						{
							id: 'remote-control',
							title: routeLabels['remote-control'],
							url: ROUTES.remoteControl()
						},
						{ id: 'agents', title: routeLabels.agents, url: ROUTES.agents() }
					]
				},
				{
					id: 'settings',
					title: routeLabels.settings,
					url: ROUTES.settings(),
					icon: Settings2Icon
				}
			]
		}
	]);

	const shownMain = $derived(visible(main));
	const shownFooter = $derived(visible(footer));

	return {
		get bountyOn() {
			return bountyOn;
		},
		get all(): NavGroup[] {
			return [...main, ...footer];
		},
		get main() {
			return shownMain;
		},
		get footer() {
			return shownFooter;
		}
	};
}
