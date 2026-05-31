import { TargetType } from '$lib/types/target';

// can be used for ease of external links for targets

export interface ExternalLink {
	label: string;
	url: string;
}

export function getExternalLinksTargetDropdown(
	targetValue: string,
	targetType: TargetType
): ExternalLink[] {
	const v = encodeURIComponent(targetValue);
	const isIp = targetType === TargetType.IP;
	const isAsn = targetType === TargetType.ASN;

	const links: Array<ExternalLink & { types: TargetType[] }> = [
		{
			label: 'Shodan',
			url: isIp
				? `https://www.shodan.io/host/${targetValue}`
				: `https://www.shodan.io/search?query=${v}`,
			types: [TargetType.DOMAIN, TargetType.IP, TargetType.IP_RANGE]
		},
		{
			label: 'Censys',
			url: `https://search.censys.io/search?resource=hosts&q=${v}`,
			types: [TargetType.DOMAIN, TargetType.IP, TargetType.IP_RANGE]
		},
		{
			label: 'VirusTotal',
			url: isIp
				? `https://www.virustotal.com/gui/ip-address/${targetValue}`
				: `https://www.virustotal.com/gui/domain/${targetValue}`,
			types: [TargetType.DOMAIN, TargetType.IP, TargetType.URL]
		},
		{
			label: 'SecurityTrails',
			url: `https://securitytrails.com/domain/${targetValue}`,
			types: [TargetType.DOMAIN]
		},
		{
			label: 'BGP.tools',
			url: isAsn
				? `https://bgp.tools/as/${targetValue.replace(/^AS/i, '')}`
				: `https://bgp.tools/prefix/${targetValue}`,
			types: [TargetType.ASN, TargetType.IP_RANGE]
		}
	];

	return links
		.filter((link) => link.types.includes(targetType))
		.map(({ label, url }) => ({ label, url }));
}
