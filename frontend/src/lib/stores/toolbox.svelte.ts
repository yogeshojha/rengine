import { toolboxApi } from '$lib/api/toolbox';
import { TOOLBOX_POLL_MS } from '$lib/config/toolbox';
import type { ToolboxCatalog, ToolRun, ToolSpec } from '$lib/types/toolbox';

const PENDING = new Set(['queued', 'running']);

function createToolboxStore() {
	let catalog = $state<ToolboxCatalog | null>(null);
	let loadingCatalog = $state(false);
	let catalogError = $state<string | null>(null);
	let runs = $state<ToolRun[]>([]);
	let busy = $state(false);
	let timer: ReturnType<typeof setTimeout> | null = null;

	function upsert(run: ToolRun) {
		runs = [run, ...runs.filter((r) => r.id !== run.id)];
	}

	function stopPolling() {
		if (timer) clearTimeout(timer);
		timer = null;
	}

	function poll(id: string) {
		stopPolling();
		timer = setTimeout(async () => {
			try {
				const next = await toolboxApi.get(id);
				upsert(next);
				if (PENDING.has(next.status)) poll(id);
				else busy = false;
			} catch {
				busy = false;
			}
		}, TOOLBOX_POLL_MS);
	}

	return {
		get catalog() {
			return catalog;
		},
		get tools() {
			return catalog?.tools ?? [];
		},
		get groups() {
			return catalog?.groups ?? [];
		},
		get loadingCatalog() {
			return loadingCatalog;
		},
		get catalogError() {
			return catalogError;
		},
		get runs() {
			return runs;
		},
		get history() {
			return runs;
		},
		get busy() {
			return busy;
		},

		tool(name: string): ToolSpec | undefined {
			return catalog?.tools.find((t) => t.name === name);
		},

		lastRun(tool: string): ToolRun | undefined {
			return runs.find((r) => r.tool === tool);
		},

		async load(force = false) {
			if (loadingCatalog || (catalog && !force)) return;
			loadingCatalog = true;
			catalogError = null;
			try {
				catalog = await toolboxApi.catalog();
			} catch (e) {
				catalogError = e instanceof Error ? e.message : 'Toolbox not loaded';
			} finally {
				loadingCatalog = false;
			}
			void this.loadHistory();
		},

		async loadHistory() {
			try {
				runs = await toolboxApi.runs();
			} catch {
				runs = [];
			}
		},

		async run(tool: string, input: Record<string, unknown>, projectId?: string) {
			busy = true;
			stopPolling();
			try {
				const run = await toolboxApi.run({ tool, input, project_id: projectId });
				upsert(run);
				if (PENDING.has(run.status)) poll(run.id);
				else busy = false;
				return run;
			} catch (e) {
				busy = false;
				throw e;
			}
		},

		async clear() {
			stopPolling();
			busy = false;
			runs = [];
			await toolboxApi.clear();
		},

		reset() {
			stopPolling();
			catalog = null;
			catalogError = null;
			runs = [];
			busy = false;
		}
	};
}

export const toolbox = createToolboxStore();
