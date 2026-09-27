"""API key providers grouped by what each adds."""

from shared.enums.api_key import ProviderGroup

PROVIDER_GROUP_LABELS: dict[str, str] = {
    ProviderGroup.SUBDOMAINS.value: "Subdomain sources",
    ProviderGroup.LOOKUPS.value: "Lookups",
    ProviderGroup.EXPLOIT_INTEL.value: "Exploit intelligence",
    ProviderGroup.BOUNTY_PLATFORMS.value: "Bug bounty platforms",
    ProviderGroup.OAST.value: "Out-of-band testing",
    ProviderGroup.CHAT.value: "Chat",
}

# the groups the setup key step shows
RECON_GROUPS: tuple[str, ...] = (
    ProviderGroup.SUBDOMAINS.value,
    ProviderGroup.LOOKUPS.value,
    ProviderGroup.EXPLOIT_INTEL.value,
)
