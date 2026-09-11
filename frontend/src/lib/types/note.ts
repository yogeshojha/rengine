export type NoteStatus = 'open' | 'resolved';

export const NOTE_STATUSES: NoteStatus[] = ['open', 'resolved'];

export const NOTE_STATUS_LABELS: Record<NoteStatus, string> = {
	open: 'Open',
	resolved: 'Resolved'
};

export interface NoteTag {
	id: string;
	name: string;
	slug: string;
	color: string;
}

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
	tags: NoteTag[];
	created_by: string;
	author: string | null;
	created_at: string;
	updated_at: string;
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
	tag_ids: string[];
}

export interface NoteUpdate {
	title?: string | null;
	body?: string;
	status?: NoteStatus;
	tag_ids?: string[];
}

export interface NoteCount {
	key: string;
	total: number;
	open: number;
}

export interface NoteFilter {
	target_id?: string;
	scan_id?: string;
	dimension?: string;
	asset_key?: string;
	tag?: string[];
	status?: NoteStatus[];
	search?: string;
	page?: number;
	size?: number;
}
