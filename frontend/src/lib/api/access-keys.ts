import { api } from './client';
import type {
	AccessKey,
	AccessKeyCreate,
	AccessKeyCreated,
	ReferenceGroup
} from '$lib/types/access-key';

const user = (userId: string) => `/users/${encodeURIComponent(userId)}/access-keys`;

export const accessKeysApi = {
	list(): Promise<AccessKey[]> {
		return api.get<AccessKey[]>('/access-keys');
	},

	create(body: AccessKeyCreate): Promise<AccessKeyCreated> {
		return api.post<AccessKeyCreated>('/access-keys', body);
	},

	revoke(keyId: string): Promise<void> {
		return api.delete<void>(`/access-keys/${encodeURIComponent(keyId)}`);
	},

	listFor(userId: string): Promise<AccessKey[]> {
		return api.get<AccessKey[]>(user(userId));
	},

	revokeFor(userId: string, keyId: string): Promise<void> {
		return api.delete<void>(`${user(userId)}/${encodeURIComponent(keyId)}`);
	},

	reference(): Promise<ReferenceGroup[]> {
		return api.get<ReferenceGroup[]>('/reference');
	}
};
