import { api } from './client';
import type {
	APIKeyRead,
	APIKeyCreate,
	APIKeyUpdate,
	ProviderInfo
} from '$lib/types/api-key';

export const apiKeysApi = {
	async listProviders(): Promise<ProviderInfo[]> {
		return api.get<ProviderInfo[]>('/api-keys/providers');
	},

	async list(): Promise<APIKeyRead[]> {
		return api.get<APIKeyRead[]>('/api-keys');
	},

	async create(data: APIKeyCreate): Promise<APIKeyRead> {
		return api.post<APIKeyRead>('/api-keys', data);
	},

	async update(keyId: string, data: APIKeyUpdate): Promise<APIKeyRead> {
		return api.patch<APIKeyRead>(`/api-keys/${keyId}`, data);
	},

	async delete(keyId: string): Promise<void> {
		return api.delete(`/api-keys/${keyId}`);
	},

	async reveal(keyId: string): Promise<{ key_value: string }> {
		return api.get(`/api-keys/${keyId}/reveal`);
	},

	async test(keyId: string): Promise<{ provider: string; success: boolean; message: string }> {
		return api.post(`/api-keys/${keyId}/test`);
	}
};
