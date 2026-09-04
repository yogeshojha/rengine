const ACCENTS: Record<string, string> = {
	'/dashboard': 'var(--chart-1)',
	'/targets': 'var(--chart-3)',
	'/scans': 'var(--chart-2)',
	'/schedules': 'var(--chart-5)',
	'/automation': 'var(--chart-4)',
	'/arsenal': 'var(--chart-1)'
};

export function navAccent(url: string): string | null {
	const key = Object.keys(ACCENTS).find((k) => url === k || url.startsWith(`${k}/`));
	return key ? ACCENTS[key] : null;
}
