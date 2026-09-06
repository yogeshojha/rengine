import type { Recheck, RecheckChange, RescanCreate, RescanSchema } from '$lib/types/recheck';

const LIVE = new Set(['pending', 'running']);

export const isRecheckLive = (r: Recheck): boolean => LIVE.has(r.status);

export const recheckFailed = (r: Recheck): boolean => r.status === 'failed';

function phrase(c: RecheckChange): string {
	const label = c.label.toLowerCase();
	if (c.before && c.after) return `${label} ${c.before} → ${c.after}`;
	if (c.after) return `${label} ${c.after}`;
	return `no ${label}`;
}

export function recheckLabel(r: Recheck): string {
	if (isRecheckLive(r)) return 'rechecking';
	if (recheckFailed(r)) return 'recheck failed';
	if (!r.changed) return 'unchanged';
	const status = r.changes.find((c) => c.field === 'http_status');
	if (status) return status.after ? `now ${status.after}` : 'no answer';
	if (r.changes.length === 1) return phrase(r.changes[0]);
	return `${r.changes.length} changes`;
}

export function recheckTone(r: Recheck): 'live' | 'changed' | 'quiet' | 'failed' {
	if (isRecheckLive(r)) return 'live';
	if (recheckFailed(r)) return 'failed';
	return r.changed ? 'changed' : 'quiet';
}

export async function startRescan(
	projectId: string,
	body: RescanCreate,
	noun: string,
	nounPlural: string
): Promise<boolean> {
	if (!body.assets.length) return false;
	const { rechecks } = await import('$lib/stores/rechecks.svelte');
	const { toast } = await import('svelte-sonner');
	try {
		await rechecks.rescan(projectId, body);
		const n = body.assets.length;
		toast.success(`Rechecking ${n} ${n === 1 ? noun : nounPlural}`, {
			description: 'Results land on the rows as they arrive.'
		});
		return true;
	} catch (e) {
		toast.error(e instanceof Error ? e.message : 'Rescan could not start');
		return false;
	}
}

export function stagesForDimension(
	schema: RescanSchema | null,
	dimension: string
): readonly string[] {
	return schema?.dimensions.find((d) => d.dimension === dimension)?.default_stages ?? [];
}

export function seedKindFor(schema: RescanSchema | null, dimension: string): string {
	return schema?.dimensions.find((d) => d.dimension === dimension)?.seed_kind ?? 'host';
}
