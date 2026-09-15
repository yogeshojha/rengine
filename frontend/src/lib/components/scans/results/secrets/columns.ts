import type { SortOption } from '../table/columns';

export type SecretSortKey = 'state' | 'kind' | 'hosts' | 'seen';

export const SECRET_SORTS: SortOption[] = [
	{ key: 'state', label: 'State' },
	{ key: 'hosts', label: 'Web assets' },
	{ key: 'kind', label: 'Kind' },
	{ key: 'seen', label: 'Seen' }
];

export const SECRET_WIDTHS = {
	target: 'hidden w-[150px] shrink-0 lg:flex',
	kind: 'hidden w-[190px] shrink-0 md:flex',
	state: 'flex w-[100px] shrink-0',
	asset: 'hidden w-[220px] shrink-0 lg:flex',
	seen: 'hidden w-[90px] shrink-0 justify-end sm:flex',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;
