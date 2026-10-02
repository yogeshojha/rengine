import { notesApi } from '$lib/api/notes';
import type {
	Note,
	NoteCreate,
	NoteFacets,
	NoteFilter,
	NoteTagCount,
	NoteUpdate
} from '$lib/types/note';

class NotesStore {
	version = $state(0);

	async list(projectId: string, filter: NoteFilter = {}) {
		return notesApi.list(projectId, filter);
	}

	async facets(projectId: string, filter: NoteFilter = {}, assetQuery = ''): Promise<NoteFacets> {
		return notesApi.facets(projectId, filter, assetQuery);
	}

	async get(projectId: string, id: string): Promise<Note> {
		return notesApi.get(projectId, id);
	}

	async tags(projectId: string, q = ''): Promise<NoteTagCount[]> {
		return notesApi.tags(projectId, q);
	}

	async create(projectId: string, body: NoteCreate): Promise<Note> {
		const note = await notesApi.create(projectId, body);
		this.touch();
		return note;
	}

	async update(projectId: string, id: string, body: NoteUpdate): Promise<Note> {
		const note = await notesApi.update(projectId, id, body);
		this.touch();
		return note;
	}

	async remove(projectId: string, note: Note): Promise<void> {
		await notesApi.remove(projectId, note.id);
		this.touch();
	}

	/** Notes changed outside this store. */
	touch(): void {
		this.version += 1;
	}

	reset(): void {
		this.version = 0;
	}
}

export const notes = new NotesStore();
