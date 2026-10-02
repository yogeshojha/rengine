export const TRACKER_COL = {
	tracker: 'min-w-0 flex-1',
	destination: 'hidden w-[180px] shrink-0 @xl/trackers:block',
	issues: 'hidden w-[110px] shrink-0 @2xl/trackers:block',
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
	findings: 'hidden w-[110px] shrink-0 @xl/issues:block',
	filed: 'hidden w-[100px] shrink-0 @3xl/issues:block',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const BODY_ROW =
	'flex items-start gap-4 border-b border-border/60 px-4 py-2.5 last:border-b-0';
