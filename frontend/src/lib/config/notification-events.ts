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
		hint: 'Run summaries, failed runs and exploit intelligence',
		capability: null
	},
	{
		type: 'vulnerability',
		label: 'New findings',
		hint: 'Findings and known exploited software CVEs',
		capability: null
	},
	{
		type: 'integration',
		label: 'Program changes',
		hint: 'Scope changes on followed programs',
		capability: Capability.BOUNTY_PROGRAMS
	},
	{
		type: 'watch',
		label: 'Program watches',
		hint: 'New in-scope assets',
		capability: Capability.PROGRAM_WATCHES
	},
	{
		type: 'new_checks',
		label: 'New checks',
		hint: 'Findings from checks added to the library',
		capability: null
	},
	{
		type: 'tripwire',
		label: 'Tripwires',
		hint: 'Saved query matches and rescan results',
		capability: null
	},
	{
		type: 'system',
		label: 'Report failures',
		hint: 'Reports and exports that did not complete',
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
