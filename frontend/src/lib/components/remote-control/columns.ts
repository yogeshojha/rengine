export const CHAT_COL = {
	chat: 'min-w-0 flex-1',
	account: 'hidden w-[160px] shrink-0 @xl/chats:block',
	project: 'hidden w-[150px] shrink-0 @3xl/chats:block',
	capabilities: 'w-[112px] shrink-0',
	last: 'hidden w-[180px] shrink-0 @2xl/chats:block',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const CALL_COL = {
	time: 'w-[84px] shrink-0',
	chat: 'hidden w-[150px] shrink-0 @xl/calls:block',
	command: 'min-w-0 flex-1',
	result: 'hidden w-[280px] shrink-0 @2xl/calls:flex'
} as const;
