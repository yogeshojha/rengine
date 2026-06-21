import { APIProvider } from '$lib/types/api-key';

export enum InstanceMode {
	BugBounty = 'bug_bounty',
	Corporate = 'corporate'
}

export const MODE_LABELS: Record<InstanceMode, string> = {
	[InstanceMode.BugBounty]: 'Bug Bounty',
	[InstanceMode.Corporate]: 'Corporate'
};

export const INSTANCE_MODES: { value: InstanceMode; label: string }[] = [
	{ value: InstanceMode.BugBounty, label: MODE_LABELS[InstanceMode.BugBounty] },
	{ value: InstanceMode.Corporate, label: MODE_LABELS[InstanceMode.Corporate] }
];

export const DEFAULT_INSTANCE_MODE = InstanceMode.BugBounty;

export function coerceInstanceMode(value: string | null | undefined): InstanceMode {
	return value === InstanceMode.Corporate ? InstanceMode.Corporate : InstanceMode.BugBounty;
}

export const Capability = {
	HACKERONE: 'hackerone',
	BOUNTY_PROGRAMS: 'bounty_programs',
	BB_RECON_PRESETS: 'bb_recon_presets'
} as const;
export type CapabilityKey = (typeof Capability)[keyof typeof Capability];

const MODE_CAPABILITIES: Record<InstanceMode, CapabilityKey[]> = {
	[InstanceMode.BugBounty]: [
		Capability.HACKERONE,
		Capability.BOUNTY_PROGRAMS,
		Capability.BB_RECON_PRESETS
	],
	[InstanceMode.Corporate]: []
};

export const BUG_BOUNTY_ONLY_PROVIDERS: APIProvider[] = [APIProvider.HACKERONE];

export function capabilitiesForMode(mode: string | null | undefined): CapabilityKey[] {
	return MODE_CAPABILITIES[coerceInstanceMode(mode)];
}

export function modeHas(mode: string | null | undefined, capability: CapabilityKey): boolean {
	return capabilitiesForMode(mode).includes(capability);
}

export function providerAllowed(mode: string | null | undefined, provider: APIProvider): boolean {
	if (BUG_BOUNTY_ONLY_PROVIDERS.includes(provider)) {
		return modeHas(mode, Capability.HACKERONE);
	}
	return true;
}
