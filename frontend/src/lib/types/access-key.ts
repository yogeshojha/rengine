import type { AccessKeyLevel } from '$lib/config/access-keys';

export interface AccessKey {
	id: string;
	name: string;
	prefix: string;
	access: AccessKeyLevel;
	expires_at: string | null;
	expired: boolean;
	last_used_at: string | null;
	last_used_ip: string | null;
	use_count: number;
	created_at: string;
}

export interface AccessKeyCreated extends AccessKey {
	key: string;
	first_request: string;
}

export interface AccessKeyCreate {
	name: string;
	access: AccessKeyLevel;
	expires_in_days: number | null;
}

// mirrors shared/models/reference.py
export interface ReferenceParameter {
	name: string;
	location: string;
	required: boolean;
	type: string;
	description: string | null;
}

export interface ReferenceOperation {
	group: string;
	method: string;
	path: string;
	summary: string;
	access: AccessKeyLevel;
	parameters: ReferenceParameter[];
	example: unknown;
	curl: string;
}

export interface ReferenceGroup {
	name: string;
	operations: ReferenceOperation[];
}
