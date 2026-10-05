export const SOURCE_IP_SERVICE = 'Cloudflare';
export const SOURCE_IP_TIMEOUT_SECONDS = 5;

export enum SourceIpState {
	OFF = 'off',
	MEASURED = 'measured'
}

export enum SourceIpPhase {
	START = 'start',
	END = 'end'
}

export enum AddressFamily {
	IPV4 = 'ipv4',
	IPV6 = 'ipv6'
}

export enum SourceIpFailure {
	TIMEOUT = 'timeout',
	PROXY = 'proxy',
	UNREACHABLE = 'unreachable',
	NO_ADDRESS = 'no_address',
	PROXY_UNREADABLE = 'proxy_unreadable'
}

export const FAMILY_ORDER: readonly AddressFamily[] = [AddressFamily.IPV4, AddressFamily.IPV6];

export const SOURCE_IP_FAILURE_LABELS: Record<SourceIpFailure, string> = {
	[SourceIpFailure.TIMEOUT]: `${SOURCE_IP_SERVICE} did not answer within ${SOURCE_IP_TIMEOUT_SECONDS} seconds.`,
	[SourceIpFailure.PROXY]: "The scan's proxy did not complete the lookup.",
	[SourceIpFailure.UNREACHABLE]: `${SOURCE_IP_SERVICE} was unreachable.`,
	[SourceIpFailure.NO_ADDRESS]: `${SOURCE_IP_SERVICE} returned no address.`,
	[SourceIpFailure.PROXY_UNREADABLE]: 'The proxy on this run could not be read.'
};

export const SOURCE_IP_OFF_REASON = 'Record source IP was off when this scan started.';
