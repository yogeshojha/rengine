import type { TableColumn } from '$lib/components/scans/results/table/columns';

export const TRACKER_COL = {
	tracker: 'min-w-0 flex-1',
	destination: 'hidden w-[180px] shrink-0 @xl/trackers:block',
	issues: 'hidden w-[110px] shrink-0 text-right tabular-nums @2xl/trackers:block',
	check: 'w-[140px] shrink-0',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const ROUTE_COL = {
	scope: 'min-w-0 flex-1',
	tracker: 'w-[180px] shrink-0',
	destination: 'hidden w-[180px] shrink-0 @xl/routes:block',
	type: 'hidden w-[120px] shrink-0 @2xl/routes:block',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const ISSUE_COL = {
	issue: 'w-[170px] shrink-0',
	title: 'min-w-0 flex-1',
	target: 'hidden w-[180px] shrink-0 @2xl/issues:block',
	findings: 'hidden w-[110px] shrink-0 text-right tabular-nums @xl/issues:block',
	filed: 'hidden w-[100px] shrink-0 @3xl/issues:block',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const BODY_ROW =
	'flex items-start gap-3 border-b border-border/60 px-4 py-2.5 transition-colors last:border-b-0 hover:bg-muted/30';

export const TRACKER_SKELETON: TableColumn[] = [
	{ key: 'tracker', label: 'Tracker', width: TRACKER_COL.tracker },
	{ key: 'destination', label: 'Default destination', width: TRACKER_COL.destination },
	{ key: 'issues', label: 'Issues', width: TRACKER_COL.issues, align: 'right' },
	{ key: 'check', label: 'Connection', width: TRACKER_COL.check },
	{ key: 'actions', label: '', width: TRACKER_COL.actions }
];

export const ISSUE_SKELETON: TableColumn[] = [
	{ key: 'issue', label: 'Issue', width: ISSUE_COL.issue },
	{ key: 'title', label: 'Title', width: ISSUE_COL.title },
	{ key: 'target', label: 'Target', width: ISSUE_COL.target },
	{ key: 'findings', label: 'Findings', width: ISSUE_COL.findings, align: 'right' },
	{ key: 'filed', label: 'Filed', width: ISSUE_COL.filed },
	{ key: 'actions', label: '', width: ISSUE_COL.actions }
];
