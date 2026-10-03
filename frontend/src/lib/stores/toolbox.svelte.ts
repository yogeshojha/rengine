import { toolboxApi } from '$lib/api/toolbox';
import { TOOLBOX_POLL_MS } from '$lib/config/toolbox';
import type { ToolboxCatalog, ToolboxLaunch, ToolRun, ToolSpec } from '$lib/types/toolbox';

const PENDING = new Set(['queued', 'running']);
const POLL_RETRIES = 5;

function createToolboxStore() {
	let catalog = $state<ToolboxCatalog | null>(null);
	let loadingCatalog = $state(false);
	let catalogError = $state<string | null>(null);
	let runs = $state<ToolRun[]>([]);
	let historyError = $state<string | null>(null);
	let busy = $state(false);
	let dialogOpen = $state(false);
	let launch = $state<ToolboxLaunch | null>(null);
	let timer: ReturnType<typeof setTimeout> | null = null;
	let chain = 0;

	function upsert(run: ToolRun) {
		runs = [run, ...runs.filter((r) => r.id !== run.id)];
	}

	function stopPolling() {
		chain++;
		if (timer) clearTimeout(timer);
		timer = null;
	}

	function poll(id: string, misses = 0) {
		stopPolling();
		const mine = chain;
		timer = setTimeout(
			async () => {
				try {
					const next = await toolboxApi.get(id);
					if (mine !== chain) return;
					upsert(next);
					if (PENDING.has(next.status)) return poll(id);
				} catch {
					if (mine !== chain) return;
					if (misses < POLL_RETRIES) return poll(id, misses + 1);
				}
				timer = null;
				busy = false;
			},
			TOOLBOX_POLL_MS * (misses + 1)
		);
	}

	return {
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
		get historyError() {
			return historyError;
		},
		get busy() {
			return busy;
		},
		get dialogOpen() {
			return dialogOpen;
		},
		set dialogOpen(value: boolean) {
			dialogOpen = value;
		},
		get launch() {
			return launch;
		},
		set launch(value: ToolboxLaunch | null) {
			launch = value;
		},

		/** Opens the toolbox, optionally on one tool with a value, optionally running it. */
		open(request: ToolboxLaunch | null = null) {
			launch = request;
			dialogOpen = true;
		},

		tool(name: string): ToolSpec | undefined {
			return catalog?.tools.find((t) => t.name === name);
		},

		lastRun(tool: string): ToolRun | undefined {
			return runs.find((r) => r.tool === tool);
		},

		async load(force = false) {
			if (catalog && !force) {
				void this.loadHistory();
				return;
			}
			if (loadingCatalog) return;
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
				historyError = null;
				const live = runs.find((r) => PENDING.has(r.status));
				if (live && !timer) {
					busy = true;
					poll(live.id);
				}
			} catch (e) {
				historyError = e instanceof Error ? e.message : 'Recent runs not loaded';
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
			await toolboxApi.clear();
			stopPolling();
			busy = false;
			runs = [];
		},

		reset() {
			stopPolling();
			dialogOpen = false;
			launch = null;
			catalog = null;
			catalogError = null;
			runs = [];
			historyError = null;
			busy = false;
		}
	};
}

export const toolbox = createToolboxStore();
