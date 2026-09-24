export const FCOL = {
	select: 'hidden w-5 shrink-0 items-center @xl/findings:flex',
	severity: 'w-[72px] shrink-0',
	finding: 'min-w-0 flex-1',
	target: 'hidden w-[140px] shrink-0 @min-[88rem]/findings:flex',
	asset: 'hidden w-[248px] shrink-0 @4xl/findings:flex',
	related: 'hidden w-[150px] shrink-0 @6xl/findings:flex',
	risk: 'hidden w-[132px] shrink-0 @7xl/findings:flex',
	evidence: 'hidden w-[104px] shrink-0 @min-[96rem]/findings:flex',
	review: 'hidden w-[104px] shrink-0 @5xl/findings:flex',
	seen: 'hidden w-[60px] shrink-0 justify-end @xl/findings:flex',
	actions: 'flex w-[60px] shrink-0 justify-end'
} as const;

export const NARROW = {
	origin: '@4xl/findings:hidden',
	related: '@6xl/findings:hidden',
	review: '@5xl/findings:hidden',
	target: '@min-[88rem]/findings:hidden'
} as const;
