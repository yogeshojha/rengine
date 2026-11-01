// mirrors shared/enums/api_key.py:ProviderGroup
export enum ProviderGroup {
	SUBDOMAINS = 'subdomains',
	INTERNET_SCANS = 'internet_scans',
	LOOKUPS = 'lookups',
	EXPLOIT_INTEL = 'exploit_intel',
	BOUNTY_PLATFORMS = 'bounty_platforms',
	OAST = 'oast',
	CHAT = 'chat'
}

// mirrors shared/definitions/api_keys.py:RECON_GROUPS
export const RECON_GROUPS: ProviderGroup[] = [
	ProviderGroup.SUBDOMAINS,
	ProviderGroup.INTERNET_SCANS,
	ProviderGroup.LOOKUPS,
	ProviderGroup.EXPLOIT_INTEL
];

export function accountMeta(
	account: { field: string } | null,
	value: string
): { key_meta?: Record<string, string> } {
	return account ? { key_meta: { [account.field]: value.trim() } } : {};
}
