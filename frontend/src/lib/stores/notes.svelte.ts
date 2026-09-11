import { SvelteMap } from 'svelte/reactivity';
import { notesApi } from '$lib/api/notes';
import { tagsApi, type Tag } from '$lib/api/tags';
import type { Note, NoteCount, NoteCreate, NoteFilter, NoteUpdate } from '$lib/types/note';

function countKey(dimension: string, scope: string): string {
	return `${dimension}:${scope}`;
}

class NotesStore {
	tags = $state<Tag[]>([]);
	private counts = new SvelteMap<string, SvelteMap<string, NoteCount>>();
	private tagsProjectId: string | null = null;
	private tagsPending: Promise<void> | null = null;
	private countsPending = new Map<string, Promise<void>>();

	async loadTags(projectSlug: string, projectId: string): Promise<void> {
		if (this.tagsProjectId === projectId) return;
		this.tagsPending ??= tagsApi
			.list({ project_slug: projectSlug })
			.then((rows) => {
				this.tags = rows;
				this.tagsProjectId = projectId;
			})
			.catch(() => {})
			.finally(() => {
				this.tagsPending = null;
			});
		return this.tagsPending;
	}

	countFor(dimension: string, scope: string, assetKey: string): NoteCount | null {
		return this.counts.get(countKey(dimension, scope))?.get(assetKey) ?? null;
	}

	async loadCounts(
		projectId: string,
		dimension: string,
		scope: { scan_id?: string; target_id?: string } = {}
	): Promise<void> {
		const key = countKey(dimension, scope.scan_id ?? scope.target_id ?? 'project');
		const inflight = this.countsPending.get(key);
		if (inflight) return inflight;
		const pending = notesApi
			.counts(projectId, { dimension, ...scope })
			.then((rows) => {
				const map = new SvelteMap<string, NoteCount>();
				for (const row of rows) map.set(row.key, row);
				this.counts.set(key, map);
			})
			.catch(() => {})
			.finally(() => {
				this.countsPending.delete(key);
			});
		this.countsPending.set(key, pending);
		return pending;
	}

	async list(projectId: string, filter: NoteFilter = {}) {
		return notesApi.list(projectId, filter);
	}

	async create(projectId: string, body: NoteCreate): Promise<Note> {
		const note = await notesApi.create(projectId, body);
		this.bump(note, 1);
		return note;
	}

	async update(projectId: string, id: string, body: NoteUpdate): Promise<Note> {
		return notesApi.update(projectId, id, body);
	}

	async remove(projectId: string, note: Note): Promise<void> {
		await notesApi.remove(projectId, note.id);
		this.bump(note, -1);
	}

	reset(): void {
		this.tags = [];
		this.tagsProjectId = null;
		this.counts.clear();
		this.countsPending.clear();
	}

	/** Keep the row markers in step without another round trip. */
	private bump(note: Note, by: number): void {
		if (!note.dimension || !note.asset_key) return;
		for (const [key, map] of this.counts) {
			if (!key.startsWith(`${note.dimension}:`)) continue;
			const current = map.get(note.asset_key);
			const total = Math.max(0, (current?.total ?? 0) + by);
			if (total === 0) map.delete(note.asset_key);
			else
				map.set(note.asset_key, {
					key: note.asset_key,
					total,
					open: Math.max(0, (current?.open ?? 0) + (note.status === 'open' ? by : 0))
				});
		}
	}
}

export const notes = new NotesStore();
