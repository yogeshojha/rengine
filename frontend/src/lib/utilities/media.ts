import { API_PREFIX } from '$lib/api/client';

export function screenshotUrl(path: string | null | undefined): string | null {
	if (!path) return null;
	return `${API_PREFIX}/media/screenshot?path=${encodeURIComponent(path)}`;
}
