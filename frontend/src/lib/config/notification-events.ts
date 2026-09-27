import { Capability, type CapabilityKey } from '$lib/config/capabilities';

// mirrors shared/definitions/notification_events.py
export interface ChannelEvent {
	type: string;
	label: string;
	hint: string;
	capability: CapabilityKey | null;
}

export const CHANNEL_EVENTS: ChannelEvent[] = [
	{
		type: 'scan',
		label: 'Scan results',
		hint: 'Run digest, failed runs, exposures and exploit intelligence changes',
		capability: null
	},
	{
		type: 'vulnerability',
		label: 'New vulnerabilities',
		hint: 'New findings and inferred software CVEs',
		capability: null
	},
	{
		type: 'integration',
		label: 'Program changes',
		hint: 'Scope and status changes on bug bounty programs',
		capability: Capability.BOUNTY_PROGRAMS
	},
	{
		type: 'watch',
		label: 'Program watches',
		hint: 'New in-scope assets on a watched program',
		capability: Capability.PROGRAM_WATCHES
	},
	{
		type: 'new_checks',
		label: 'New checks',
		hint: 'Library additions and follow-up run results',
		capability: null
	},
	{
		type: 'system',
		label: 'Reports and exports',
		hint: 'Ready or failed',
		capability: null
	},
	{
		type: 'target',
		label: 'Enrichment',
		hint: 'Failed WHOIS and BGP lookups',
		capability: null
	}
];

export const DEFAULT_CHANNEL_EVENTS: string[] = CHANNEL_EVENTS.map((event) => event.type);

export interface ChannelLevel {
	value: string;
	label: string;
}

export const CHANNEL_LEVELS: ChannelLevel[] = [
	{ value: 'info', label: 'All events' },
	{ value: 'warning', label: 'Warnings and errors' },
	{ value: 'error', label: 'Errors only' }
];

export const DEFAULT_CHANNEL_LEVEL = 'info';

export function channelEventsFor(has: (capability: CapabilityKey) => boolean): ChannelEvent[] {
	return CHANNEL_EVENTS.filter((event) => !event.capability || has(event.capability));
}
