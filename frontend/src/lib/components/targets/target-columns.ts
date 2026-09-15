import type { TableColumn } from '$lib/components/scans/results/table/columns';

export const TARGET_WIDTHS = {
	name: 'flex min-w-0 flex-1',
	type: 'hidden w-[84px] shrink-0 sm:flex',
	organizations: 'hidden w-[170px] shrink-0 md:block',
	tags: 'hidden w-[170px] shrink-0 lg:block',
	updated: 'hidden w-[92px] shrink-0 justify-end sm:flex',
	actions: 'flex w-[68px] shrink-0 gap-1'
} as const;

export const TARGET_SKELETON_COLUMNS: TableColumn[] = [
	{ key: 'name', label: 'Target', width: TARGET_WIDTHS.name },
	{ key: 'type', label: 'Type', width: TARGET_WIDTHS.type },
	{ key: 'organizations', label: 'Organizations', width: TARGET_WIDTHS.organizations },
	{ key: 'tags', label: 'Tags', width: TARGET_WIDTHS.tags },
	{ key: 'updated', label: 'Updated', width: TARGET_WIDTHS.updated, align: 'right' },
	{ key: 'actions', label: '', width: TARGET_WIDTHS.actions }
];
