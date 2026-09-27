// mirrors shared/enums/api_key.py:ProviderGroup
export enum ProviderGroup {
	SUBDOMAINS = 'subdomains',
	LOOKUPS = 'lookups',
	EXPLOIT_INTEL = 'exploit_intel',
	BOUNTY_PLATFORMS = 'bounty_platforms',
	OAST = 'oast',
	CHAT = 'chat'
}

// mirrors shared/definitions/api_keys.py:RECON_GROUPS
export const RECON_GROUPS: ProviderGroup[] = [
	ProviderGroup.SUBDOMAINS,
	ProviderGroup.LOOKUPS,
	ProviderGroup.EXPLOIT_INTEL
];
