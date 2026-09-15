import { STORAGE_KEYS } from '$lib/config/storage-keys';
import { SURFACE_ORDER, type SurfaceDimension } from '$lib/config/surface';

const VISIT_LIMIT = 8;
const SEARCH_LIMIT = 6;

export type VisitKind = 'target' | 'scan';

export interface Visit {
	kind: VisitKind;
	id: string;
	label: string;
	projectId: string;
	at: number;
}

export interface RecentSearch {
	dimension: SurfaceDimension;
	query: string;
}

function read(): Visit[] {
	if (typeof localStorage === 'undefined') return [];
	try {
		const raw = localStorage.getItem(STORAGE_KEYS.paletteRecents);
		const parsed: unknown = raw ? JSON.parse(raw) : [];
		return Array.isArray(parsed) ? (parsed as Visit[]) : [];
	} catch {
		return [];
	}
}

function write(entries: Visit[]) {
	try {
		localStorage.setItem(STORAGE_KEYS.paletteRecents, JSON.stringify(entries));
	} catch {
		/* storage unavailable */
	}
}

function readQueries(key: string): string[] {
	if (typeof localStorage === 'undefined') return [];
	try {
		const raw = localStorage.getItem(key);
		const parsed: unknown = raw ? JSON.parse(raw) : [];
		return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : [];
	} catch {
		return [];
	}
}

function createRecentStore() {
	let visits = $state<Visit[]>(read());

	return {
		get visits() {
			return visits;
		},

		/** The last places opened in one project, newest first. */
		opened(projectId: string): Visit[] {
			return visits.filter((v) => v.projectId === projectId);
		},

		record(entry: Omit<Visit, 'at'>) {
			if (!entry.id || !entry.label || !entry.projectId) return;
			const head = visits[0];
			if (head?.kind === entry.kind && head.id === entry.id && head.label === entry.label) return;
			const next = [
				{ ...entry, at: Date.now() },
				...visits.filter((v) => !(v.kind === entry.kind && v.id === entry.id))
			].slice(0, VISIT_LIMIT);
			visits = next;
			write(next);
		},

		forget(kind: VisitKind, id: string) {
			const next = visits.filter((v) => !(v.kind === kind && v.id === id));
			visits = next;
			write(next);
		},

		/** One query per dimension per round, so no dimension crowds the list. */
		searches(): RecentSearch[] {
			const lanes = SURFACE_ORDER.map((spec) => ({
				dimension: spec.key,
				queries: readQueries(spec.recentsKey)
			}));
			const out: RecentSearch[] = [];
			const depth = Math.max(0, ...lanes.map((lane) => lane.queries.length));
			for (let i = 0; i < depth && out.length < SEARCH_LIMIT; i += 1) {
				for (const lane of lanes) {
					const query = lane.queries[i];
					if (!query || out.some((r) => r.query === query)) continue;
					out.push({ dimension: lane.dimension, query });
					if (out.length >= SEARCH_LIMIT) break;
				}
			}
			return out;
		},

		reset() {
			visits = [];
			write([]);
		}
	};
}

export const recent = createRecentStore();
