import { MODE_LABELS, type InstanceMode } from '$lib/config/capabilities';
import type { About, CheckLibrary } from '$lib/types/about';

export const NOT_AVAILABLE = 'Not available';

export function modeLabel(mode: string): string {
	return MODE_LABELS[mode as InstanceMode] ?? mode;
}

export function checkCount(library: CheckLibrary): string | null {
	if (library.version) return library.version;
	return library.checks == null ? null : `${library.checks.toLocaleString('en-US')} checks`;
}

function utcStamp(iso: string): string {
	return `${new Date(iso).toISOString().slice(0, 16).replace('T', ' ')} UTC`;
}

function libraryLine(library: CheckLibrary | null): string {
	if (!library) return NOT_AVAILABLE;
	const parts = [checkCount(library), library.synced_at && `synced ${utcStamp(library.synced_at)}`];
	return parts.filter(Boolean).join(', ') || NOT_AVAILABLE;
}

/** Markdown for the Environment field of a GitHub issue. */
export function aboutDetails(about: About): string {
	const lines = [
		`- reNgine: ${about.version}`,
		`- Mode: ${modeLabel(about.mode)}`,
		`- Architecture: ${about.architecture ?? NOT_AVAILABLE}`,
		`- PostgreSQL: ${about.postgres ?? NOT_AVAILABLE}`,
		`- Redis: ${about.redis ?? NOT_AVAILABLE}`,
		`- Check library: ${libraryLine(about.check_library)}`,
		'- Tools:',
		...about.tools.map((tool) => `  - ${tool.name} ${tool.version}`)
	];
	return lines.join('\n');
}
