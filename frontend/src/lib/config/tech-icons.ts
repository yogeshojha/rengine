const TECH_ICON_BASE = '/tech-icons';

export function techIconSlug(name: string): string {
	return name
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '');
}

export function techIconUrl(name: string): string | null {
	const slug = techIconSlug(name.split(':')[0]);
	return slug ? `${TECH_ICON_BASE}/${slug}.svg` : null;
}
