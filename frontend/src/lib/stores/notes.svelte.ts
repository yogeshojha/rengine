import { notesApi } from '$lib/api/notes';
import { tagsApi, type Tag } from '$lib/api/tags';
import type { Note, NoteCreate, NoteFilter, NoteUpdate } from '$lib/types/note';

class NotesStore {
	tags = $state<Tag[]>([]);
	version = $state(0);
	private tagsProjectId: string | null = null;
	private tagsPending = new Map<string, Promise<void>>();

	async loadTags(projectSlug: string, projectId: string): Promise<void> {
		if (this.tagsProjectId === projectId) return;
		const inflight = this.tagsPending.get(projectId);
		if (inflight) return inflight;
		const pending = tagsApi
			.list({ project_slug: projectSlug })
			.then((rows) => {
				this.tags = rows;
				this.tagsProjectId = projectId;
			})
			.catch(() => {})
			.finally(() => {
				this.tagsPending.delete(projectId);
			});
		this.tagsPending.set(projectId, pending);
		return pending;
	}

	async list(projectId: string, filter: NoteFilter = {}) {
		return notesApi.list(projectId, filter);
	}

	async create(projectId: string, body: NoteCreate): Promise<Note> {
		const note = await notesApi.create(projectId, body);
		this.version += 1;
		return note;
	}

	async update(projectId: string, id: string, body: NoteUpdate): Promise<Note> {
		return notesApi.update(projectId, id, body);
	}

	async remove(projectId: string, note: Note): Promise<void> {
		await notesApi.remove(projectId, note.id);
		this.version += 1;
	}

	reset(): void {
		this.tags = [];
		this.tagsProjectId = null;
		this.tagsPending.clear();
	}
}

export const notes = new NotesStore();
