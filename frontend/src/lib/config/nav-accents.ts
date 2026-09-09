const ACCENTS: Record<string, string> = {
	'/dashboard': 'var(--chart-1)',
	'/targets': 'var(--chart-3)',
	'/surface/web-assets': 'var(--chart-1)',
	'/surface/endpoints': 'var(--chart-2)',
	'/surface/services': 'var(--chart-3)',
	'/surface/ips': 'var(--chart-5)',
	'/surface/vulnerabilities': 'var(--destructive)',
	'/scans': 'var(--chart-2)',
	'/schedules': 'var(--chart-5)',
	'/automation': 'var(--chart-4)',
	'/arsenal': 'var(--chart-1)',
	'/interest': 'var(--chart-2)',
	'/bounty-hub': 'var(--chart-4)',
	'/reports': 'var(--chart-3)',
	'/ai': 'var(--chart-4)',
	'/mcp': 'var(--chart-5)',
	'/connectors': 'var(--chart-2)'
};

export function navAccent(url: string): string | null {
	const key = Object.keys(ACCENTS).find((k) => url === k || url.startsWith(`${k}/`));
	return key ? ACCENTS[key] : null;
}
