import { api } from './client';

export interface UserSummary {
	id: string;
	username: string;
}

const cache = new Map<string, Promise<UserSummary>>();

export const usersApi = {
	getSummary(userId: string): Promise<UserSummary> {
		const cached = cache.get(userId);
		if (cached) return cached;
		const request = api.get<UserSummary>(`/users/${userId}/summary`).catch((err) => {
			cache.delete(userId);
			throw err;
		});
		cache.set(userId, request);
		return request;
	}
};
