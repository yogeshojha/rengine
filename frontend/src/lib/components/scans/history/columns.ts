// columns show by the table's own width (@container/scans), not the window's
export const COL = {
	select: 'w-6 shrink-0',
	target: 'min-w-[200px] max-w-[420px] flex-1',
	status: 'ml-auto w-[124px] shrink-0',
	findings: 'w-[150px] shrink-0',
	assets: 'hidden w-[208px] shrink-0 @3xl/scans:flex',
	change: 'hidden w-[96px] shrink-0 @5xl/scans:flex',
	engine: 'hidden w-[150px] shrink-0 @7xl/scans:block',
	duration: 'hidden w-[64px] shrink-0 justify-end @5xl/scans:flex',
	started: 'flex w-[72px] shrink-0 justify-end',
	actions: 'flex w-[60px] shrink-0 justify-end'
} as const;
