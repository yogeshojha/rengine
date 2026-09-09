import Wrench from '@lucide/svelte/icons/wrench';
import Server from '@lucide/svelte/icons/server';
import Route from '@lucide/svelte/icons/route';
import ScrollText from '@lucide/svelte/icons/scroll-text';
import ListTree from '@lucide/svelte/icons/list-tree';
import Network from '@lucide/svelte/icons/network';
import GitFork from '@lucide/svelte/icons/git-fork';
import Globe from '@lucide/svelte/icons/globe';
import ShieldAlert from '@lucide/svelte/icons/shield-alert';
import type { IconComponent } from './icons';
import type { Tone } from '$lib/types/toolbox';

export const TOOL_ICONS: Record<string, IconComponent> = {
	'scroll-text': ScrollText,
	'list-tree': ListTree,
	network: Network,
	'git-fork': GitFork,
	globe: Globe,
	'shield-alert': ShieldAlert
};

export const TOOLBOX_ICON = Wrench;

export function toolIcon(slug: string): IconComponent {
	return TOOL_ICONS[slug] ?? Wrench;
}

const GLYPHS: Record<string, IconComponent> = {
	...TOOL_ICONS,
	server: Server,
	route: Route
};

export function glyphIcon(slug: string): IconComponent | null {
	return GLYPHS[slug] ?? null;
}

export const TONE_TEXT: Record<Tone, string> = {
	neutral: 'text-foreground',
	success: 'text-success',
	warning: 'text-warning',
	critical: 'text-destructive',
	info: 'text-info',
	muted: 'text-muted-foreground'
};

export const TONE_DOT: Record<Tone, string> = {
	neutral: 'bg-muted-foreground/40',
	success: 'bg-success',
	warning: 'bg-warning',
	critical: 'bg-destructive',
	info: 'bg-info',
	muted: 'bg-muted-foreground/30'
};

export const TONE_CHIP: Record<Tone, string> = {
	neutral: 'border-border bg-muted/40 text-foreground',
	success: 'border-success/25 bg-success/10 text-success',
	warning: 'border-warning/25 bg-warning/10 text-warning',
	critical: 'border-destructive/25 bg-destructive/10 text-destructive',
	info: 'border-info/25 bg-info/10 text-info',
	muted: 'border-border bg-muted/30 text-muted-foreground'
};

export const TONE_METER: Record<Tone, string> = {
	neutral: 'bg-foreground/70',
	success: 'bg-success',
	warning: 'bg-warning',
	critical: 'bg-destructive',
	info: 'bg-info',
	muted: 'bg-muted-foreground/40'
};

export const TOOLBOX_POLL_MS = 900;
