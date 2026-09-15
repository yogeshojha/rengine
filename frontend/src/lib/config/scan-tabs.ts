import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
import ScanEye from '@lucide/svelte/icons/scan-eye';
import Share2 from '@lucide/svelte/icons/share-2';
import StickyNote from '@lucide/svelte/icons/sticky-note';
import type { IconComponent } from './icons';
import { RESULT_TABS, SURFACE_ORDER } from './surface';
import { INTEREST_TAB } from './interest';
import { CORRELATION_TAB } from './correlation';

export const OVERVIEW_TAB = 'overview';
export const NOTES_TAB = 'notes';

export const SCAN_TABS = [
	OVERVIEW_TAB,
	INTEREST_TAB,
	...RESULT_TABS,
	CORRELATION_TAB,
	NOTES_TAB
] as const;
export type ScanTab = (typeof SCAN_TABS)[number];

export interface ScanTabSpec {
	key: ScanTab;
	label: string;
	icon: IconComponent;
}

export const SCAN_TAB_DEFS: ScanTabSpec[] = [
	{ key: OVERVIEW_TAB, label: 'Overview', icon: LayoutDashboard },
	{ key: INTEREST_TAB as ScanTab, label: 'Exposures', icon: ScanEye },
	...SURFACE_ORDER.map((s) => ({ key: s.tab as ScanTab, label: s.label, icon: s.icon })),
	{ key: CORRELATION_TAB as ScanTab, label: 'Correlation', icon: Share2 },
	{ key: NOTES_TAB as ScanTab, label: 'Notes', icon: StickyNote }
];

export const PINNED_SCAN_TABS: ScanTab[] = [OVERVIEW_TAB];
