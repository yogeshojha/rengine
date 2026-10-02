import { api } from './client';
import type { Wordlist, WordlistUpload, WordlistUploadResult } from '$lib/types/wordlist';

export const wordlistsApi = {
	list(): Promise<Wordlist[]> {
		return api.get<Wordlist[]>('/wordlists');
	},

	upload(body: WordlistUpload): Promise<WordlistUploadResult> {
		return api.post<WordlistUploadResult>('/wordlists', body);
	},

	preview(id: string, limit = 100): Promise<string[]> {
		return api.get<string[]>(`/wordlists/${id}/preview?limit=${limit}`);
	},

	remove(id: string): Promise<void> {
		return api.delete<void>(`/wordlists/${id}`);
	}
};
