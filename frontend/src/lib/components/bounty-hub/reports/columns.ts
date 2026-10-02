export const RCOL = {
	report: 'min-w-[240px] flex-1 contain-inline-size',
	program: 'hidden w-[180px] shrink-0 md:block',
	severity: 'w-[92px] shrink-0',
	state: 'w-[124px] shrink-0',
	bounty: 'flex w-[88px] shrink-0 justify-end',
	submitted: 'hidden w-[76px] shrink-0 justify-end sm:flex',
	actions: 'flex w-[60px] shrink-0 justify-end'
} as const;

export const PCOL = {
	program: 'min-w-[200px] flex-1 contain-inline-size',
	outcome: 'w-[220px] shrink-0',
	severity: 'hidden w-[120px] shrink-0 md:flex',
	paid: 'hidden w-[64px] shrink-0 justify-end sm:flex',
	earned: 'flex w-[96px] shrink-0 justify-end',
	last: 'hidden w-[108px] shrink-0 justify-end lg:flex',
	actions: 'flex w-[36px] shrink-0 justify-end'
} as const;
