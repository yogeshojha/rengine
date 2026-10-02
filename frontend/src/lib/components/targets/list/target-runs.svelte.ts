import { SvelteMap, SvelteSet } from 'svelte/reactivity';
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
	known = new SvelteSet<string>();
	#seq = 0;

	async load(projectId: string, targetIds: string[]) {
		const mine = ++this.#seq;
		if (!projectId || targetIds.length === 0) {
			this.runs.clear();
			this.trends.clear();
			this.known.clear();
			return;
		}
		const parts = chunks(targetIds);
		let runs: ScanRead[][];
		let trends: ScanTargetTrend[][];
		try {
			[runs, trends] = await Promise.all([
				Promise.all(parts.map((p) => scansApi.latest(projectId, p))),
				Promise.all(parts.map((p) => scansApi.trends(projectId, p)))
			]);
		} catch {
			if (mine === this.#seq) for (const id of targetIds) this.known.add(id);
			return;
		}
		if (mine !== this.#seq) return;
		this.runs.clear();
		for (const r of runs.flat()) this.runs.set(r.target_id, r);
		this.trends.clear();
		for (const t of trends.flat()) this.trends.set(t.target_id, t);
		this.known.clear();
		for (const id of targetIds) this.known.add(id);
	}
}
