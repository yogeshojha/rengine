import { SvelteMap, SvelteSet } from 'svelte/reactivity';
import { scansApi } from '$lib/api/scans';
import type { Recheck, RescanCreate, RescanSchema } from '$lib/types/recheck';
import type { ScanRead } from '$lib/types/scan';
import { isRecheckLive } from '$lib/utilities/rechecks';

const POLL_MS = 3000;

class RechecksStore {
	schema = $state<RescanSchema | null>(null);
	private byScan = new SvelteMap<string, SvelteMap<string, Recheck[]>>();
	private timers = new Map<string, ReturnType<typeof setTimeout>>();
	private schemaPending: Promise<void> | null = null;

	async loadSchema(): Promise<void> {
		if (this.schema) return;
		this.schemaPending ??= scansApi
			.rescanSchema()
			.then((s) => {
				this.schema = s;
			})
			.catch(() => {})
			.finally(() => {
				this.schemaPending = null;
			});
		return this.schemaPending;
	}

	dimension(key: string) {
		return this.schema?.dimensions.find((d) => d.dimension === key) ?? null;
	}

	latest(scanId: string, assetKey: string): Recheck | null {
		return this.byScan.get(scanId)?.get(assetKey)?.[0] ?? null;
	}

	history(scanId: string, assetKey: string): Recheck[] {
		return this.byScan.get(scanId)?.get(assetKey) ?? [];
	}

	touched(scanId: string): SvelteSet<string> {
		return new SvelteSet(this.byScan.get(scanId)?.keys() ?? []);
	}

	async load(scanId: string, projectId: string): Promise<void> {
		if (!scanId || !projectId) return;
		try {
			this.index(scanId, await scansApi.rechecks(projectId, scanId));
		} catch {
			return;
		}
		this.schedule(scanId, projectId);
	}

	async rescan(projectId: string, body: RescanCreate): Promise<ScanRead> {
		const scan = await scansApi.rescan(projectId, body);
		this.optimistic(body, scan);
		this.schedule(body.parent_scan_id, projectId, 800);
		return scan;
	}

	stop(scanId: string): void {
		const timer = this.timers.get(scanId);
		if (timer) clearTimeout(timer);
		this.timers.delete(scanId);
	}

	reset(): void {
		for (const timer of this.timers.values()) clearTimeout(timer);
		this.timers.clear();
		this.byScan.clear();
		this.schema = null;
	}

	private index(scanId: string, rows: Recheck[]): void {
		const map = new SvelteMap<string, Recheck[]>();
		for (const row of rows) {
			const bucket = map.get(row.asset_key);
			if (bucket) bucket.push(row);
			else map.set(row.asset_key, [row]);
		}
		this.byScan.set(scanId, map);
	}

	// the chip must move on the click, not on the first poll
	private optimistic(body: RescanCreate, scan: ScanRead): void {
		const map = new SvelteMap(this.byScan.get(body.parent_scan_id) ?? []);
		for (const asset of body.assets) {
			const pending: Recheck = {
				id: scan.id,
				scan_id: scan.id,
				parent_scan_id: body.parent_scan_id,
				dimension: body.dimension,
				asset_kind: this.dimension(body.dimension)?.seed_kind ?? 'host',
				asset_key: asset,
				changed: false,
				changes: [],
				created_at: scan.created_at,
				status: scan.status,
				stage_titles: [],
				duration_seconds: null
			};
			map.set(asset, [pending, ...(map.get(asset) ?? [])]);
		}
		this.byScan.set(body.parent_scan_id, map);
	}

	private schedule(scanId: string, projectId: string, delay = POLL_MS): void {
		this.stop(scanId);
		const live = [...(this.byScan.get(scanId)?.values() ?? [])].some((rows) =>
			rows.some(isRecheckLive)
		);
		if (!live) return;
		this.timers.set(
			scanId,
			setTimeout(() => {
				this.timers.delete(scanId);
				void this.load(scanId, projectId);
			}, delay)
		);
	}
}

export const rechecks = new RechecksStore();
