const ACCENTS: Record<string, string> = {
	'/dashboard': 'var(--chart-1)',
	'/surface/web-assets': 'var(--chart-1)',
	'/surface/endpoints': 'var(--chart-2)',
	'/surface/services': 'var(--chart-3)',
	'/surface/ips': 'var(--chart-5)',
	'/surface/vulnerabilities': 'var(--destructive)',
	'/exposures': 'var(--chart-4)',
	'/bounty-hub': 'var(--chart-4)',
	'/targets': 'var(--chart-3)',
	'/scans': 'var(--chart-2)',
	'/connectors': 'var(--chart-2)',
	'/reports': 'var(--chart-3)',
	'/arsenal': 'var(--chart-1)',
	'/automation': 'var(--chart-4)'
};

export function navAccent(url: string): string | null {
	const key = Object.keys(ACCENTS).find((k) => url === k || url.startsWith(`${k}/`));
	return key ? ACCENTS[key] : null;
}
