import { SvelteMap, SvelteSet } from 'svelte/reactivity';
import { exportsApi } from '$lib/api/exports';
import { isLive } from '$lib/config/exports';
import type { ExportCreate, ExportRead } from '$lib/types/export';

// a small export finishes inside the fast window and downloads without a second click
const FAST_MS = 300;
const FAST_FOR_MS = 4000;
const SLOW_MS = 1800;

function createExportsStore() {
	let rows = $state<ExportRead[]>([]);
	let loading = $state(false);
	let creating = $state(false);
	let timer: ReturnType<typeof setTimeout> | null = null;
	let watchingSince = 0;
	let projectId = '';
	const handlers = new SvelteMap<string, (row: ExportRead) => void>();
	const awaited = new SvelteSet<string>();

	function claimHandler(id: string, handler?: (row: ExportRead) => void) {
		if (handler) handlers.set(id, handler);
	}

	function stop() {
		if (timer) clearTimeout(timer);
		timer = null;
	}

	function schedule() {
		stop();
		if (!rows.some((row) => isLive(row.status))) return;
		const fast = Date.now() - watchingSince < FAST_FOR_MS;
		timer = setTimeout(() => void refresh(), fast ? FAST_MS : SLOW_MS);
	}

	async function refresh() {
		const live = rows.filter((row) => isLive(row.status));
		await Promise.all(
			live.map(async (row) => {
				try {
					const fresh = await exportsApi.get(projectId, row.id);
					rows = rows.map((r) => (r.id === fresh.id ? fresh : r));
					if (!isLive(fresh.status) && awaited.delete(fresh.id)) {
						const handler = handlers.get(fresh.id);
						handlers.delete(fresh.id);
						handler?.(fresh);
					}
				} catch {
					/* a row that vanished stops being polled on the next pass */
				}
			})
		);
		schedule();
	}

	return {
		get rows() {
			return rows;
		},
		get loading() {
			return loading;
		},
		get creating() {
			return creating;
		},
		get liveCount() {
			return rows.filter((row) => isLive(row.status)).length;
		},

		async load(project: string, scope: { scanId?: string; targetId?: string } = {}) {
			projectId = project;
			loading = true;
			try {
				rows = await exportsApi.list(project, scope);
				watchingSince = Date.now();
				schedule();
			} finally {
				loading = false;
			}
		},

		async create(
			project: string,
			body: ExportCreate,
			onReady?: (row: ExportRead) => void
		): Promise<ExportRead | null> {
			projectId = project;
			creating = true;
			try {
				const row = await exportsApi.create(project, body);
				rows = [row, ...rows];
				claimHandler(row.id, onReady);
				awaited.add(row.id);
				watchingSince = Date.now();
				schedule();
				return row;
			} finally {
				creating = false;
			}
		},

		async rerun(id: string, onReady?: (row: ExportRead) => void): Promise<ExportRead | null> {
			const row = await exportsApi.rerun(projectId, id);
			rows = [row, ...rows];
			claimHandler(row.id, onReady);
			awaited.add(row.id);
			watchingSince = Date.now();
			schedule();
			return row;
		},

		async remove(id: string) {
			await exportsApi.remove(projectId, id);
			rows = rows.filter((row) => row.id !== id);
		},

		downloadUrl(id: string) {
			return exportsApi.downloadUrl(projectId, id);
		},

		reset() {
			stop();
			rows = [];
			projectId = '';
			awaited.clear();
			handlers.clear();
		}
	};
}

export const exportsStore = createExportsStore();
