import { VULN_STATES, VulnState } from '$lib/config/vulnerabilities';

export type NoteStatus = 'open' | 'resolved';

export const NOTE_STATUSES: NoteStatus[] = ['open', 'resolved'];

export const NOTE_STATUS_LABELS: Record<NoteStatus, string> = {
	open: 'Open',
	resolved: 'Resolved'
};

// mirrors shared/definitions/notes.py
export const MAX_NOTE_BODY = 20000;
export const MAX_NOTE_TAGS = 20;
export const MAX_NOTE_TAG_CHARS = 32;
export const NOTE_TAG_PUNCTUATION = '._-:';
export const NOTE_ASSET_SEPARATOR = ':';

export enum NoteSubject {
	TARGET = 'target',
	SCAN = 'scan'
}

export const NOTE_SUBJECT_LABELS: Record<NoteSubject, string> = {
	[NoteSubject.TARGET]: 'Targets',
	[NoteSubject.SCAN]: 'Scans'
};

export const TRIAGE_REASON_STATES: string[] = VULN_STATES.filter((s) => s !== VulnState.OPEN);

export interface Note {
	id: string;
	project_id: string;
	target_id: string;
	target_value: string;
	scan_id: string | null;
	dimension: string | null;
	asset_key: string | null;
	asset_label: string | null;
	title: string | null;
	body: string;
	status: NoteStatus;
	tags: string[];
	triage_state: string | null;
	created_by: string;
	author: string | null;
	created_at: string;
	updated_at: string;
	scan_at: string | null;
	finding_id: string | null;
}

export interface NoteAnchor {
	targetId: string;
	scanId?: string | null;
	dimension?: string | null;
	assetKey?: string | null;
	assetLabel?: string | null;
}

export interface NoteCreate {
	target_id: string;
	scan_id?: string | null;
	dimension?: string | null;
	asset_key?: string | null;
	asset_label?: string | null;
	title?: string | null;
	body: string;
	status?: NoteStatus;
	tags?: string[];
	triage_state?: string | null;
}

export interface NoteUpdate {
	title?: string | null;
	body?: string;
	status?: NoteStatus;
	tags?: string[];
}

export interface NoteFilter {
	target_id?: string | string[];
	scan_id?: string;
	scan?: string[];
	dimension?: string | string[];
	asset_key?: string;
	asset?: string[];
	tag?: string[];
	status?: NoteStatus[];
	author?: string[];
	triage?: string[];
	search?: string;
	page?: number;
	size?: number;
}

export interface NoteTagCount {
	name: string;
	count: number;
}

export interface NoteFacet {
	value: string;
	label: string | null;
	count: number;
}

export interface NoteAssetFacet extends NoteFacet {
	dimension: string;
}

export interface NoteScanFacet extends NoteFacet {
	target_value: string;
	at: string;
}

export interface NoteFacets {
	total: number;
	targets: NoteFacet[];
	dimensions: NoteFacet[];
	assets: NoteAssetFacet[];
	scans: NoteScanFacet[];
	tags: NoteFacet[];
	authors: NoteFacet[];
	statuses: NoteFacet[];
	triage: NoteFacet[];
}
