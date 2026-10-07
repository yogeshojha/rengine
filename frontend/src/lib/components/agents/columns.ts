import type { TableColumn } from '$lib/components/scans/results/table/columns';

export const AGENT_COL = {
	agent: 'min-w-0 flex-1',
	access: 'w-[104px] shrink-0',
	scope: 'hidden w-[170px] shrink-0 @2xl/agents:block',
	last: 'hidden w-[130px] shrink-0 @xl/agents:block',
	expires: 'hidden w-[120px] shrink-0 @3xl/agents:block',
	issuer: 'hidden w-[130px] shrink-0 @4xl/agents:block',
	actions: 'flex w-8 shrink-0 justify-end'
} as const;

export const AGENT_SKELETON: TableColumn[] = [
	{ key: 'agent', label: 'Agent', width: AGENT_COL.agent },
	{ key: 'access', label: 'Access', width: AGENT_COL.access },
	{ key: 'scope', label: 'Scope', width: AGENT_COL.scope },
	{ key: 'last', label: 'Last call', width: AGENT_COL.last },
	{ key: 'expires', label: 'Expires', width: AGENT_COL.expires },
	{ key: 'issuer', label: 'Issued by', width: AGENT_COL.issuer },
	{ key: 'actions', label: '', width: AGENT_COL.actions }
];
