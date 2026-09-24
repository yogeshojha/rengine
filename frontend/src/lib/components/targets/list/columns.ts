export const TCOL = {
	select: 'hidden w-5 shrink-0 items-center @xl/targets:flex',
	target: 'min-w-0 flex-1',
	run: 'hidden w-[132px] shrink-0 @2xl/targets:flex',
	findings: 'hidden w-[150px] shrink-0 @lg/targets:flex',
	assets: 'hidden w-[208px] shrink-0 @5xl/targets:flex',
	change: 'hidden w-[96px] shrink-0 @6xl/targets:flex',
	organizations: 'hidden w-[150px] shrink-0 @7xl/targets:flex',
	tags: 'hidden w-[150px] shrink-0 @min-[88rem]/targets:flex',
	actions: 'flex w-[92px] shrink-0 justify-end'
} as const;

export const TNARROW = {
	run: '@2xl/targets:hidden',
	findings: '@lg/targets:hidden',
	spark: 'hidden @3xl/targets:block'
} as const;
