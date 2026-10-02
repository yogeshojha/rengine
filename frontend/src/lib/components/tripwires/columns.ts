export const TRIPWIRE_COL = {
	tripwire: 'min-w-0 flex-1',
	fires: 'hidden w-[128px] shrink-0 @sm/tripwires:block',
	scope: 'hidden w-[160px] shrink-0 @4xl/tripwires:block',
	then: 'hidden w-[190px] shrink-0 @5xl/tripwires:block',
	last: 'hidden w-[110px] shrink-0 @2xl/tripwires:block',
	recent: 'hidden w-[84px] shrink-0 text-right @lg/tripwires:block',
	enabled: 'w-[44px] shrink-0',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;
