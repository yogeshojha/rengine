import { api, toQuery } from './client';
import type { PaginatedResponse } from '$lib/types/pagination';
import type { Note, NoteCreate, NoteFilter, NoteUpdate } from '$lib/types/note';

export const notesApi = {
	async list(projectId: string, filter: NoteFilter = {}): Promise<PaginatedResponse<Note>> {
		return api.get<PaginatedResponse<Note>>(
			`/notes${toQuery({ project_id: projectId, ...filter })}`
		);
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
