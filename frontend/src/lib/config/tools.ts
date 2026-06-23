export interface ToolSpec {
	name: string;
	label: string;
	phase: string;
	example: string;
}

export const SCAN_TOOLS: ToolSpec[] = [
	{
		name: 'subfinder',
		label: 'Subfinder',
		phase: 'Subdomain Discovery',
		example: '-all -recursive -timeout 30'
	},
	{ name: 'amass', label: 'Amass', phase: 'Subdomain Discovery', example: '-active' },
	{
		name: 'assetfinder',
		label: 'Assetfinder',
		phase: 'Subdomain Discovery',
		example: '--subs-only'
	},
	{ name: 'sublist3r', label: 'Sublist3r', phase: 'Subdomain Discovery', example: '-v' },
	{
		name: 'oneforall',
		label: 'OneForAll',
		phase: 'Subdomain Discovery',
		example: '--takeover False'
	},
	{ name: 'tlsx', label: 'TLSX', phase: 'TLS / Certificates', example: '-cn -san' },
	{ name: 'dnsx', label: 'DNSX', phase: 'DNS Resolution', example: '-rcode noerror' }
];
