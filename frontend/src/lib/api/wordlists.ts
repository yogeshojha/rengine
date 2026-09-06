import { api } from './client';
import type { Wordlist, WordlistUpload, WordlistUploadResult } from '$lib/types/wordlist';

export const wordlistsApi = {
	list(kind?: string): Promise<Wordlist[]> {
		return api.get<Wordlist[]>(`/wordlists${kind ? `?kind=${encodeURIComponent(kind)}` : ''}`);
	},

	kinds(): Promise<Record<string, string>> {
		return api.get<Record<string, string>>('/wordlists/kinds');
	},

	upload(body: WordlistUpload): Promise<WordlistUploadResult> {
		return api.post<WordlistUploadResult>('/wordlists', body);
	},

	preview(id: string, limit = 100): Promise<string[]> {
		return api.get<string[]>(`/wordlists/${id}/preview?limit=${limit}`);
	},

	rename(id: string, data: { name?: string; description?: string }): Promise<Wordlist> {
		return api.patch<Wordlist>(`/wordlists/${id}`, data);
	},

	remove(id: string): Promise<void> {
		return api.delete<void>(`/wordlists/${id}`);
	}
};
