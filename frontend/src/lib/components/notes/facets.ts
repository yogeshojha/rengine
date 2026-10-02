import Hash from '@lucide/svelte/icons/hash';
import type { IconComponent } from '$lib/config/icons';
import { SURFACE_ORDER, surfaceSpec } from '$lib/config/surface';
import { VULN_STATE_LABELS, VULN_STATES } from '$lib/config/vulnerabilities';
import { formatShortDate } from '$lib/utilities/dates';
import {
	NOTE_STATUS_LABELS,
	NOTE_STATUSES,
	NOTE_SUBJECT_LABELS,
	NoteSubject,
	type NoteFacet,
	type NoteFacets,
	type NoteStatus
} from '$lib/types/note';

export interface FacetOption {
	value: string;
	label: string;
	count: number;
	icon?: IconComponent;
	mono?: boolean;
}

// the notes page filters, by url param
export const NOTE_FACETS = [
	{ param: 'target', title: 'Target' },
	{ param: 'type', title: 'Asset type' },
	{ param: 'asset', title: 'Asset' },
	{ param: 'scan', title: 'Scan' },
	{ param: 'tag', title: 'Tag' },
	{ param: 'author', title: 'Author' },
	{ param: 'status', title: 'Status' },
	{ param: 'triage', title: 'Triage' }
] as const;

export type NoteFacetParam = (typeof NOTE_FACETS)[number]['param'];

const KIND_ORDER: string[] = [
	...SURFACE_ORDER.map((spec) => spec.key as string),
	NoteSubject.TARGET,
	NoteSubject.SCAN
];

function ordered(rows: NoteFacet[], order: string[]): NoteFacet[] {
	return [...rows].sort((a, b) => order.indexOf(a.value) - order.indexOf(b.value));
}

export function kindLabel(value: string): string {
	return surfaceSpec(value)?.label ?? NOTE_SUBJECT_LABELS[value as NoteSubject] ?? value;
}

/** Each facet's options, labelled for the toolbar. */
export function facetOptions(facets: NoteFacets | null): Record<NoteFacetParam, FacetOption[]> {
	return {
		target: (facets?.targets ?? []).map((f) => ({
			value: f.value,
			label: f.label ?? f.value,
			count: f.count,
			mono: true
		})),
		type: ordered(facets?.dimensions ?? [], KIND_ORDER).map((f) => ({
			value: f.value,
			label: kindLabel(f.value),
			count: f.count,
			icon: surfaceSpec(f.value)?.icon
		})),
		asset: (facets?.assets ?? []).map((f) => ({
			value: f.value,
			label: f.label ?? f.value,
			count: f.count,
			icon: surfaceSpec(f.dimension)?.icon,
			mono: true
		})),
		scan: (facets?.scans ?? []).map((f) => ({
			value: f.value,
			label: `${f.target_value} · ${formatShortDate(f.at)}`,
			count: f.count
		})),
		tag: (facets?.tags ?? []).map((f) => ({
			value: f.value,
			label: f.value,
			count: f.count,
			icon: Hash,
			mono: true
		})),
		author: (facets?.authors ?? []).map((f) => ({
			value: f.value,
			label: f.label ?? f.value,
			count: f.count
		})),
		status: ordered(facets?.statuses ?? [], NOTE_STATUSES).map((f) => ({
			value: f.value,
			label: NOTE_STATUS_LABELS[f.value as NoteStatus] ?? f.value,
			count: f.count
		})),
		triage: ordered(facets?.triage ?? [], VULN_STATES).map((f) => ({
			value: f.value,
			label: VULN_STATE_LABELS[f.value] ?? f.value,
			count: f.count
		}))
	};
}

/** Options plus any pick the counts left out, at zero. */
export function withPicks(
	options: FacetOption[],
	picked: string[],
	known: (value: string) => FacetOption | undefined
): FacetOption[] {
	const listed = new Set(options.map((o) => o.value));
	const missing = picked
		.filter((value) => !listed.has(value))
		.map((value) => ({ ...(known(value) ?? { value, label: value }), count: 0 }));
	return [...missing, ...options];
}
