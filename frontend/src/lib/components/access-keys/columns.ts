import type { TableColumn } from '$lib/components/scans/results/table/columns';

export const ACCESS_KEY_COL = {
	name: 'min-w-0 flex-1',
	key: 'hidden w-[150px] shrink-0 @xl/access-keys:block',
	access: 'w-[112px] shrink-0',
	used: 'hidden w-[150px] shrink-0 @2xl/access-keys:block',
	expires: 'hidden w-[104px] shrink-0 @lg/access-keys:block',
	created: 'hidden w-[96px] shrink-0 @3xl/access-keys:block',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const PARAMETER_COL = {
	name: 'w-36 shrink-0',
	location: 'w-16 shrink-0',
	type: 'w-20 shrink-0',
	description: 'min-w-0 flex-1'
} as const;

export const ACCESS_KEY_SKELETON: TableColumn[] = [
	{ key: 'name', label: 'Name', width: ACCESS_KEY_COL.name },
	{ key: 'key', label: 'Key', width: ACCESS_KEY_COL.key },
	{ key: 'access', label: 'Access', width: ACCESS_KEY_COL.access },
	{ key: 'used', label: 'Last used', width: ACCESS_KEY_COL.used },
	{ key: 'expires', label: 'Expires', width: ACCESS_KEY_COL.expires },
	{ key: 'created', label: 'Created', width: ACCESS_KEY_COL.created },
	{ key: 'actions', label: '', width: ACCESS_KEY_COL.actions }
];
