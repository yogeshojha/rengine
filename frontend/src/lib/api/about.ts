import { api } from './client';
import type { About } from '$lib/types/about';

export const aboutApi = {
	async get(): Promise<About> {
		return api.get<About>('/about');
	}
};
