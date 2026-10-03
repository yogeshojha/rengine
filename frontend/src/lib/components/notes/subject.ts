import TargetIcon from '@lucide/svelte/icons/target';
import RadarIcon from '@lucide/svelte/icons/radar';
import type { IconComponent } from '$lib/config/icons';
import { ROUTES } from '$lib/config/routes';
import { SurfaceDimension, surfaceSpec } from '$lib/config/surface';
import { formatShortDate } from '$lib/utilities/dates';
import { splitHostPort } from '$lib/utilities/net';
import { exactToken } from '$lib/utilities/scan-insights';
import type { Note } from '$lib/types/note';
import type { User } from '$lib/api/auth';

export interface NoteSubjectView {
	icon: IconComponent;
	label: string;
	type: string;
}

const capitalized = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

export function scanLabel(at: string | null): string {
	return at ? `Scan ${formatShortDate(at)}` : 'Scan';
}

/** What a note is written on: its asset, else its scan or its target. */
export function noteSubject(note: Note): NoteSubjectView {
	const spec = note.dimension ? surfaceSpec(note.dimension) : undefined;
	if (spec)
		return {
			icon: spec.icon,
			label: note.asset_label || note.asset_key || '',
			type: capitalized(spec.noun)
		};
	if (note.scan_id)
		return { icon: RadarIcon, label: note.target_value, type: scanLabel(note.scan_at) };
	return { icon: TargetIcon, label: note.target_value, type: 'Target' };
}

/** The asset's sheet in its scan, else its results tab narrowed to it, else null. */
export function noteAssetHref(note: Note): string | null {
	const spec = note.dimension ? surfaceSpec(note.dimension) : undefined;
	const key = note.asset_key;
	if (!spec || !key) return null;
	const at = (query: Record<string, string>) => ROUTES.results(spec.tab, note.scan_id, query);
	switch (spec.key) {
		case SurfaceDimension.WEB_ASSETS:
		case SurfaceDimension.IPS:
			return spec.sheetParam ? at({ [spec.sheetParam]: key }) : null;
		case SurfaceDimension.VULNERABILITIES:
			return spec.sheetParam && note.finding_id ? at({ [spec.sheetParam]: note.finding_id }) : null;
		case SurfaceDimension.ENDPOINTS:
			return note.asset_label
				? at({ [spec.queryParam]: exactToken('url', note.asset_label), ...spec.rowView })
				: null;
		case SurfaceDimension.SERVICES: {
			const [host, port] = splitHostPort(key);
			return port
				? at({ [spec.queryParam]: `${exactToken('ip', host)} ${exactToken('port', port)}` })
				: null;
		}
		case SurfaceDimension.SECRETS:
			return at({ [spec.queryParam]: exactToken('fingerprint', key) });
		default:
			return null;
	}
}

/** Where Open lands: the asset, else the scan or the target the note is on. */
export function noteHref(note: Note): string | null {
	if (note.dimension) return noteAssetHref(note);
	return note.scan_id ? ROUTES.scan(note.scan_id) : ROUTES.target(note.target_id);
}

/** The author or an administrator edits and deletes a note. */
export function canChangeNote(
	note: Pick<Note, 'created_by'>,
	user: Pick<User, 'id' | 'is_superuser'> | null
): boolean {
	return !!user && (user.is_superuser || user.id === note.created_by);
}
