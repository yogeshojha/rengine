import type {
	FocusedRun,
	Recheck,
	RecheckChange,
	RescanCreate,
	RescanSchema,
	SeedSelection
} from '$lib/types/recheck';

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

export function selectionLabel(search: string, filters: string[]): string {
	const parts = [search.trim(), ...filters].filter(Boolean);
	return parts.length ? parts.join(' · ') : 'No filter';
}

export function runStarted(run: FocusedRun, noun: string, nounPlural: string): string {
	const n = run.asset_count;
	return `Rechecking ${n.toLocaleString()} ${n === 1 ? noun : nounPlural}`;
}

export function runDescription(run: FocusedRun): string {
	const parts: string[] = [];
	if (run.target_count > 1) parts.push(`${run.target_count} targets`);
	if (run.capped) {
		parts.push(
			run.matched === null
				? `Capped at ${run.asset_count.toLocaleString()}`
				: `Capped at ${run.asset_count.toLocaleString()} of ${run.matched.toLocaleString()}`
		);
	}
	return parts.join(' · ');
}

export async function startRescan(
	projectId: string,
	selection: SeedSelection,
	noun: string,
	nounPlural: string,
	body: Omit<RescanCreate, 'selection'> = {}
): Promise<boolean> {
	const { rechecks } = await import('$lib/stores/rechecks.svelte');
	const { toast } = await import('svelte-sonner');
	try {
		const run = await rechecks.rescan(projectId, { ...body, selection, dimension: '' });
		toast.success(runStarted(run, noun, nounPlural), { description: runDescription(run) });
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
