import { SvelteMap } from 'svelte/reactivity';
import { scansApi } from '$lib/api/scans';
import type { ScanRead, ScanTargetTrend } from '$lib/types/scan';

const CHUNK = 100;

function chunks<T>(list: T[]): T[][] {
	const out: T[][] = [];
	for (let i = 0; i < list.length; i += CHUNK) out.push(list.slice(i, i + CHUNK));
	return out;
}

export class TargetRuns {
	runs = new SvelteMap<string, ScanRead>();
	trends = new SvelteMap<string, ScanTargetTrend>();
	loaded = $state(false);
	failed = $state(false);
	#seq = 0;

	async load(projectId: string, targetIds: string[]) {
		const mine = ++this.#seq;
		if (!projectId || targetIds.length === 0) {
			this.runs.clear();
			this.trends.clear();
			this.loaded = true;
			return;
		}
		try {
			const parts = chunks(targetIds);
			const [runs, trends] = await Promise.all([
				Promise.all(parts.map((p) => scansApi.latest(projectId, p))),
				Promise.all(parts.map((p) => scansApi.trends(projectId, p)))
			]);
			if (mine !== this.#seq) return;
			this.runs.clear();
			for (const r of runs.flat()) this.runs.set(r.target_id, r);
			this.trends.clear();
			for (const t of trends.flat()) this.trends.set(t.target_id, t);
			this.failed = false;
		} catch {
			if (mine === this.#seq) this.failed = true;
		} finally {
			if (mine === this.#seq) this.loaded = true;
		}
	}
}
