import { api } from './client';
import type { PaginatedResponse } from '$lib/types/pagination';
import type { Note, NoteCount, NoteCreate, NoteFilter, NoteUpdate } from '$lib/types/note';

function params(projectId: string, filter: NoteFilter = {}): string {
	const search = new URLSearchParams({ project_id: projectId });
	for (const [key, value] of Object.entries(filter)) {
		if (value === undefined || value === null || value === '') continue;
		if (Array.isArray(value)) for (const v of value) search.append(key, String(v));
		else search.set(key, String(value));
	}
	return search.toString();
}

export const notesApi = {
	async list(projectId: string, filter: NoteFilter = {}): Promise<PaginatedResponse<Note>> {
		return api.get<PaginatedResponse<Note>>(`/notes?${params(projectId, filter)}`);
	},

	async counts(
		projectId: string,
		filter: Pick<NoteFilter, 'dimension' | 'target_id' | 'scan_id'> = {}
	): Promise<NoteCount[]> {
		return api.get<NoteCount[]>(`/notes/counts?${params(projectId, filter)}`);
	},

	async create(projectId: string, body: NoteCreate): Promise<Note> {
		return api.post<Note>(`/notes?project_id=${projectId}`, body);
	},

	async update(projectId: string, id: string, body: NoteUpdate): Promise<Note> {
		return api.patch<Note>(`/notes/${id}?project_id=${projectId}`, body);
	},

	async remove(projectId: string, id: string): Promise<void> {
		return api.delete(`/notes/${id}?project_id=${projectId}`);
	}
};
