import Ban from '@lucide/svelte/icons/ban';
import Cog from '@lucide/svelte/icons/cog';
import Crosshair from '@lucide/svelte/icons/crosshair';
import FolderOpen from '@lucide/svelte/icons/folder-open';
import GitCompareArrows from '@lucide/svelte/icons/git-compare-arrows';
import Layers from '@lucide/svelte/icons/layers';
import Link2 from '@lucide/svelte/icons/link-2';
import Monitor from '@lucide/svelte/icons/monitor';
import Moon from '@lucide/svelte/icons/moon';
import Pause from '@lucide/svelte/icons/pause';
import Play from '@lucide/svelte/icons/play';
import Sun from '@lucide/svelte/icons/sun';

import Award from '@lucide/svelte/icons/award';
import CalendarClock from '@lucide/svelte/icons/calendar-clock';
import FileText from '@lucide/svelte/icons/file-text';
import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
import Plug from '@lucide/svelte/icons/plug';
import ScanEye from '@lucide/svelte/icons/scan-eye';
import Settings2 from '@lucide/svelte/icons/settings-2';
import Share2 from '@lucide/svelte/icons/share-2';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import StickyNote from '@lucide/svelte/icons/sticky-note';
import Library from '@lucide/svelte/icons/library';
import Radar from '@lucide/svelte/icons/radar';
import Target from '@lucide/svelte/icons/target';

import type { IconComponent } from './icons';
import { Capability, type CapabilityKey } from './capabilities';
import { ROUTES, routeLabels, SETTINGS_SECTIONS } from './routes';
import { SURFACE_ORDER } from './surface';
import type { PaletteScope } from '$lib/utilities/palette';
import { isOpenStatus } from '$lib/utilities/scan-status';
import type { ScanRead } from '$lib/types/scan';
import type { Project } from '$lib/types/project';

export const PALETTE_GROUPS = ['run', 'create', 'pages', 'page', 'instance'] as const;
export type PaletteGroup = (typeof PALETTE_GROUPS)[number];

export const GROUP_LABELS: Record<PaletteGroup, string> = {
	run: 'Run',
	create: 'Create',
	pages: 'Pages',
	page: 'This page',
	instance: 'Instance'
};

export interface PaletteCommand {
	id: string;
	label: string;
	hint?: string;
	keywords?: string;
	icon: IconComponent;
	group: PaletteGroup;
	run: () => void;
}

export interface PaletteActions {
	go: (href: string) => void;
	addTarget: () => void;
	startScan: (value?: string) => void;
	pause: (scan: ScanRead) => void;
	resume: (scan: ScanRead) => void;
	cancel: (scan: ScanRead) => void;
	cancelAll: () => void;
	copyLink: () => void;
	switchProject: (project: Project) => void;
	setTheme: (mode: 'light' | 'dark' | 'system') => void;
}

export interface PaletteContext {
	scope: PaletteScope;
	liveScans: ScanRead[];
	projects: Project[];
	activeProjectId: string;
	has: (capability: CapabilityKey) => boolean;
	actions: PaletteActions;
}

const MAX_RUN_COMMANDS = 6;

const runLabel = (scan: ScanRead) => scan.execution_config.target_value ?? scan.engine_name;

function runCommands(ctx: PaletteContext): PaletteCommand[] {
	const { scope, actions } = ctx;
	const out: PaletteCommand[] = [
		{
			id: 'scan:start',
			label: 'Start scan',
			icon: Play,
			group: 'run',
			keywords: 'launch run new scan',
			run: () => actions.startScan()
		}
	];

	if (scope.targetValue) {
		out.push({
			id: 'scan:start-scoped',
			label: 'Start scan on this target',
			hint: scope.targetValue,
			icon: Play,
			group: 'run',
			keywords: `launch ${scope.targetValue}`,
			run: () => actions.startScan(scope.targetValue ?? undefined)
		});
	}

	if (scope.scanId) {
		out.push({
			id: 'scan:compare',
			label: 'Compare runs',
			hint: scope.label,
			icon: GitCompareArrows,
			group: 'run',
			keywords: 'diff changes delta',
			run: () => actions.go(ROUTES.compare(scope.scanId as string))
		});
	}

	for (const scan of ctx.liveScans
		.filter((s) => isOpenStatus(s.status))
		.slice(0, MAX_RUN_COMMANDS)) {
		const label = runLabel(scan);
		if (scan.status === 'paused') {
			out.push({
				id: `scan:resume:${scan.id}`,
				label: 'Resume scan',
				hint: label,
				icon: Play,
				group: 'run',
				keywords: label,
				run: () => actions.resume(scan)
			});
		} else {
			out.push({
				id: `scan:pause:${scan.id}`,
				label: 'Pause scan',
				hint: label,
				icon: Pause,
				group: 'run',
				keywords: label,
				run: () => actions.pause(scan)
			});
		}
		out.push({
			id: `scan:cancel:${scan.id}`,
			label: 'Cancel scan',
			hint: label,
			icon: Ban,
			group: 'run',
			keywords: `stop ${label}`,
			run: () => actions.cancel(scan)
		});
	}

	if (ctx.liveScans.length > 1) {
		out.push({
			id: 'scan:cancel-all',
			label: 'Cancel all unfinished scans',
			hint: `${ctx.liveScans.length} unfinished`,
			icon: Ban,
			group: 'run',
			keywords: 'stop all',
			run: () => actions.cancelAll()
		});
	}

	return out;
}

function createCommands(ctx: PaletteContext): PaletteCommand[] {
	return [
		{
			id: 'create:target',
			label: 'Add target',
			icon: Crosshair,
			group: 'create',
			keywords: 'new domain ip asn',
			run: () => ctx.actions.addTarget()
		},
		{
			id: 'create:engine',
			label: 'New scan engine',
			icon: Cog,
			group: 'create',
			keywords: 'configuration stages',
			run: () => ctx.actions.go(ROUTES.engine('new'))
		},
		{
			id: 'create:context',
			label: 'New scan context',
			icon: Layers,
			group: 'create',
			keywords: 'auth scope rate proxy',
			run: () => ctx.actions.go(ROUTES.newContext())
		}
	];
}

interface Destination {
	id: string;
	label: string;
	href: string;
	icon: IconComponent;
	keywords?: string;
	capability?: CapabilityKey;
}

function destinations(): Destination[] {
	const surfaces: Destination[] = SURFACE_ORDER.map((spec) => ({
		id: `page:${spec.tab}`,
		label: spec.label,
		href: ROUTES.surface(spec.tab),
		icon: spec.icon,
		keywords: spec.nounPlural
	}));

	const settings: Destination[] = SETTINGS_SECTIONS.map((section) => ({
		id: `page:settings:${section}`,
		label: `${routeLabels.settings} · ${routeLabels[section] ?? section}`,
		href: ROUTES.settings(section),
		icon: Settings2,
		keywords: section.replace(/-/g, ' '),
		capability: section === 'bounty-hub' ? Capability.BOUNTY_PLATFORMS : undefined
	}));

	return [
		{
			id: 'page:dashboard',
			label: routeLabels.dashboard,
			href: ROUTES.dashboard,
			icon: LayoutDashboard,
			keywords: 'home overview'
		},
		{
			id: 'page:targets',
			label: routeLabels.targets,
			href: ROUTES.targets,
			icon: Target,
			keywords: 'scope assets owned'
		},
		...surfaces,
		{
			id: 'page:cves',
			label: routeLabels.cves,
			href: ROUTES.cves,
			icon: ShieldAlert,
			keywords: 'kev epss exploited'
		},
		{
			id: 'page:exposures',
			label: routeLabels.exposures,
			href: ROUTES.exposures(),
			icon: ScanEye,
			keywords: 'interest rules flagged'
		},
		{
			id: 'page:correlation',
			label: routeLabels.correlation,
			href: ROUTES.correlation,
			icon: Share2,
			keywords: 'shared identity hubs graph'
		},
		{
			id: 'page:scans',
			label: routeLabels.scans,
			href: ROUTES.scans,
			icon: Radar,
			keywords: 'runs history'
		},
		{
			id: 'page:schedules',
			label: routeLabels.schedules,
			href: ROUTES.schedules,
			icon: CalendarClock,
			keywords: 'recurring cron interval'
		},
		{
			id: 'page:engines',
			label: routeLabels.engines,
			href: ROUTES.engines,
			icon: Cog,
			keywords: 'configuration stages'
		},
		{
			id: 'page:contexts',
			label: routeLabels.contexts,
			href: ROUTES.contexts,
			icon: Layers,
			keywords: 'auth scope rate proxy'
		},
		{
			id: 'page:notes',
			label: routeLabels.notes,
			href: ROUTES.notes,
			icon: StickyNote
		},
		{
			id: 'page:reports',
			label: routeLabels.reports,
			href: ROUTES.reports(),
			icon: FileText,
			keywords: 'pdf export deliverable'
		},
		{
			id: 'page:arsenal',
			label: routeLabels.arsenal,
			href: ROUTES.arsenal(),
			icon: Library,
			keywords: 'templates wordlists feeds library'
		},
		{
			id: 'page:connectors',
			label: routeLabels.connectors,
			href: ROUTES.connectors(),
			icon: Plug,
			keywords: 'burp proxy browsing'
		},
		{
			id: 'page:bounty-hub',
			label: routeLabels['bounty-hub'],
			href: ROUTES.bountyHub(),
			icon: Award,
			keywords: 'programs watching platforms',
			capability: Capability.BOUNTY_PROGRAMS
		},
		...settings
	];
}

function pageCommands(ctx: PaletteContext): PaletteCommand[] {
	return destinations()
		.filter((d) => !d.capability || ctx.has(d.capability))
		.map((d) => ({
			id: d.id,
			label: d.label,
			icon: d.icon,
			group: 'pages' as const,
			keywords: d.keywords,
			run: () => ctx.actions.go(d.href)
		}));
}

function instanceCommands(ctx: PaletteContext): PaletteCommand[] {
	const projects: PaletteCommand[] = ctx.projects
		.filter((p) => p.id !== ctx.activeProjectId)
		.map((project) => ({
			id: `project:${project.id}`,
			label: `Switch to ${project.name}`,
			hint: 'Project',
			icon: FolderOpen,
			group: 'instance' as const,
			keywords: `project ${project.slug}`,
			run: () => ctx.actions.switchProject(project)
		}));

	return [
		...projects,
		{
			id: 'theme:light',
			label: 'Light theme',
			icon: Sun,
			group: 'instance',
			keywords: 'appearance mode',
			run: () => ctx.actions.setTheme('light')
		},
		{
			id: 'theme:dark',
			label: 'Dark theme',
			icon: Moon,
			group: 'instance',
			keywords: 'appearance mode',
			run: () => ctx.actions.setTheme('dark')
		},
		{
			id: 'theme:system',
			label: 'System theme',
			icon: Monitor,
			group: 'instance',
			keywords: 'appearance mode',
			run: () => ctx.actions.setTheme('system')
		}
	];
}

export function buildCommands(ctx: PaletteContext): PaletteCommand[] {
	return [
		...runCommands(ctx),
		...createCommands(ctx),
		{
			id: 'page:copy-link',
			label: 'Copy link to this page',
			icon: Link2,
			group: 'page' as const,
			keywords: 'share url address',
			run: () => ctx.actions.copyLink()
		},
		...pageCommands(ctx),
		...instanceCommands(ctx)
	];
}

const WORD = /[^a-z0-9]+/;

/** Every word of the input must appear in the label, hint or keywords. */
export function matchCommand(command: PaletteCommand, input: string): boolean {
	const needles = input.toLowerCase().split(WORD).filter(Boolean);
	if (!needles.length) return true;
	const hay = `${command.label} ${command.hint ?? ''} ${command.keywords ?? ''}`.toLowerCase();
	return needles.every((word) => hay.includes(word));
}
