export const KEY_COL = {
	provider: 'min-w-0 flex-1',
	key: 'hidden w-[190px] shrink-0 @2xl/keys:block',
	status: 'w-[112px] shrink-0',
	tested: 'hidden w-[104px] shrink-0 @xl/keys:block',
	actions: 'flex w-[84px] shrink-0 justify-end'
} as const;

export const PROXY_COL = {
	proxy: 'min-w-0 flex-1',
	endpoint: 'hidden w-[230px] shrink-0 @2xl/proxies:block',
	contexts: 'hidden w-[96px] shrink-0 @xl/proxies:block',
	status: 'w-[128px] shrink-0',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const CHANNEL_COL = {
	channel: 'min-w-0 flex-1',
	events: 'hidden w-[190px] shrink-0 @2xl/channels:block',
	level: 'hidden w-[150px] shrink-0 @xl/channels:block',
	delivery: 'w-[140px] shrink-0',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const USER_COL = {
	user: 'min-w-0 flex-1',
	role: 'w-[104px] shrink-0',
	twoFactor: 'hidden w-[104px] shrink-0 @xl/users:block',
	created: 'hidden w-[120px] shrink-0 @2xl/users:block',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const CALL_COL = {
	when: 'w-[72px] shrink-0',
	feature: 'min-w-0 flex-1',
	model: 'hidden min-w-0 flex-1 @2xl/calls:block',
	input: 'hidden w-[104px] shrink-0 text-right @xl/calls:block',
	output: 'hidden w-[104px] shrink-0 text-right @xl/calls:block',
	cost: 'w-[56px] shrink-0 text-right',
	outcome: 'w-[56px] shrink-0'
} as const;

export const CONNECTION_COL = {
	use: 'flex w-4 shrink-0 items-center gap-2 @md/ai:w-[72px]',
	provider: 'min-w-0 flex-1',
	model: 'hidden w-[200px] shrink-0 @lg/ai:block',
	key: 'hidden w-[150px] shrink-0 @2xl/ai:block',
	status: 'w-[112px] shrink-0',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const USAGE_COL = {
	feature: 'min-w-0 flex-1',
	calls: 'w-[64px] shrink-0 text-right',
	cached: 'hidden w-[64px] shrink-0 text-right @2xl/usage:block',
	failed: 'hidden w-[64px] shrink-0 text-right @2xl/usage:block',
	input: 'hidden w-[104px] shrink-0 text-right @xl/usage:block',
	output: 'hidden w-[104px] shrink-0 text-right @xl/usage:block',
	cost: 'w-[72px] shrink-0 text-right'
} as const;

export const HEAD_ROW =
	'flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase';

export const BODY_ROW =
	'flex items-center gap-3 border-b border-border/60 px-4 py-2.5 transition-colors last:border-b-0 hover:bg-muted/30';

export const GROUP_ROW =
	'border-b border-border/60 bg-muted/10 px-4 pt-3 pb-1.5 text-2xs font-semibold tracking-[0.08em] text-muted-foreground uppercase';
