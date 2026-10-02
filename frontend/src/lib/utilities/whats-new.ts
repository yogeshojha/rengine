import { ROUTES } from '$lib/config/routes';
import { SURFACE } from '$lib/config/surface';
import { KIND_DIMENSION, NewKind, type NewKindKey } from '$lib/config/whats-new';
import type { NewItem, VisualPair } from '$lib/types/whats-new';

/** Where a row opens. */
export function rowHref(row: NewItem): string | null {
	const dimension = KIND_DIMENSION[row.kind as NewKindKey];
	if (dimension && row.scan_id) {
		const spec = SURFACE[dimension];
		return ROUTES.scanTab(row.scan_id, spec.tab, row.query ? { [spec.queryParam]: row.query } : {});
	}
	switch (row.kind) {
		case NewKind.CERT_HOST:
			return row.scan_id
				? ROUTES.scan(row.scan_id)
				: row.watch_id
					? ROUTES.bountyWatch(row.watch_id)
					: null;
		case NewKind.TARGET:
			return row.target_id ? ROUTES.target(row.target_id) : null;
		default:
			return row.handle ? ROUTES.bountyHub(row.handle, row.platform ?? undefined) : null;
	}
}

export function visualChange(pair: VisualPair, field: string): string {
	switch (field) {
		case 'http_status':
			return `${pair.before_status ?? '—'} → ${pair.after_status ?? '—'}`;
		case 'page_title':
			return `${pair.before_title ?? 'No title'} → ${pair.after_title ?? 'No title'}`;
		case 'webserver':
			return `${pair.before_server ?? '—'} → ${pair.after_server ?? '—'}`;
		case 'tech': {
			const before = new Set(pair.before_tech);
			const after = new Set(pair.after_tech);
			const added = pair.after_tech.filter((t) => !before.has(t)).map((t) => `+${t}`);
			const gone = pair.before_tech.filter((t) => !after.has(t)).map((t) => `−${t}`);
			return [...added, ...gone].join(' ');
		}
		default:
			return field;
	}
}
