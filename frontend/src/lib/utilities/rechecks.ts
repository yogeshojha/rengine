import type {
	FocusedRun,
	Recheck,
	RecheckChange,
	RescanCreate,
	RescanSchema,
	SeedSelection
} from '$lib/types/recheck';
import type { ScanStatus } from '$lib/types/scan';
import { isLiveStatus } from '$lib/utilities/scan-status';

export const isRecheckLive = (r: Recheck): boolean => isLiveStatus(r.status as ScanStatus);

export const recheckFailed = (r: Recheck): boolean => r.status === 'failed';

export const recheckPaused = (r: Recheck): boolean => r.status === 'paused';

function phrase(c: RecheckChange): string {
	const label = c.label.toLowerCase();
	if (c.before && c.after) return `${label} ${c.before} → ${c.after}`;
	if (c.after) return `${label} ${c.after}`;
	return `no ${label}`;
}

export function recheckLabel(r: Recheck): string {
	if (isRecheckLive(r)) return 'rechecking';
	if (recheckFailed(r)) return 'recheck failed';
	if (recheckPaused(r)) return 'recheck paused';
	if (!r.changed) return 'unchanged';
	const status = r.changes.find((c) => c.field === 'http_status');
	if (status) return status.after ? `now ${status.after}` : 'no answer';
	if (r.changes.length === 1) return phrase(r.changes[0]);
	return `${r.changes.length} changes`;
}

export function recheckTone(r: Recheck): 'live' | 'changed' | 'quiet' | 'failed' {
	if (isRecheckLive(r)) return 'live';
	if (recheckFailed(r)) return 'failed';
	if (recheckPaused(r)) return 'quiet';
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

export function cappedLabel(run: { asset_count: number; matched: number | null }): string {
	return run.matched === null
		? `Capped at ${run.asset_count.toLocaleString()}`
		: `Capped at ${run.asset_count.toLocaleString()} of ${run.matched.toLocaleString()}`;
}

export function runDescription(run: FocusedRun): string {
	const parts: string[] = [];
	if (run.target_count > 1) parts.push(`${run.target_count} targets`);
	if (run.capped) parts.push(cappedLabel(run));
	return parts.join(' · ');
}

export const MAX_RUN_TEMPLATES = 50;

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
		const run = await rechecks.rescan(projectId, { ...body, selection });
		toast.success(runStarted(run, noun, nounPlural), { description: runDescription(run) });
		return true;
	} catch (e) {
		toast.error(e instanceof Error ? e.message : 'Rescan not started');
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
