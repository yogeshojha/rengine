import type { SortOption, TableColumn } from '../table/columns';

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

export function secretSkeletonColumns(projectWide: boolean): TableColumn[] {
	const cols: TableColumn[] = [{ key: 'secret', label: 'Secret', width: 'min-w-0 flex-1' }];
	if (projectWide) cols.push({ key: 'target', label: 'Target', width: SECRET_WIDTHS.target });
	cols.push(
		{ key: 'kind', label: 'Kind', width: SECRET_WIDTHS.kind },
		{ key: 'state', label: 'State', width: SECRET_WIDTHS.state },
		{ key: 'asset', label: 'Web asset', width: SECRET_WIDTHS.asset },
		{ key: 'seen', label: 'Seen', width: SECRET_WIDTHS.seen, align: 'right' },
		{ key: 'actions', label: '', width: SECRET_WIDTHS.actions, align: 'right' }
	);
	return cols;
}
