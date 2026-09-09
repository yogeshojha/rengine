import { toolboxApi } from '$lib/api/toolbox';
import { TOOLBOX_POLL_MS } from '$lib/config/toolbox';
import type { LookupResult, ToolboxCatalog, ToolRun, ToolSpec } from '$lib/types/toolbox';

const PENDING = new Set(['queued', 'running']);

function createToolboxStore() {
	let catalog = $state<ToolboxCatalog | null>(null);
	let loadingCatalog = $state(false);
	let catalogError = $state<string | null>(null);
	let history = $state<ToolRun[]>([]);
	let subject = $state<LookupResult | null>(null);
	let runs = $state<ToolRun[]>([]);
	let busy = $state(false);
	let error = $state<string | null>(null);
	let timer: ReturnType<typeof setTimeout> | null = null;

	const pending = () => runs.filter((r) => PENDING.has(r.status)).map((r) => r.id);

	function stopPolling() {
		if (timer) clearTimeout(timer);
		timer = null;
	}

	function schedule() {
		stopPolling();
		if (!pending().length) return;
		timer = setTimeout(async () => {
			const settled = await Promise.all(
				pending().map((id) => toolboxApi.get(id).catch(() => null))
			);
			for (const next of settled) if (next) replace(next);
			schedule();
		}, TOOLBOX_POLL_MS);
	}

	function replace(run: ToolRun) {
		const at = runs.findIndex((r) => r.id === run.id);
		runs = at === -1 ? [...runs, run] : runs.with(at, run);
		history = [run, ...history.filter((r) => r.id !== run.id)];
	}

	return {
		get catalog() {
			return catalog;
		},
		get tools() {
			return catalog?.tools ?? [];
		},
		get loadingCatalog() {
			return loadingCatalog;
		},
		get catalogError() {
			return catalogError;
		},
		get history() {
			return history;
		},
		get subject() {
			return subject;
		},
		get runs() {
			return runs;
		},
		get busy() {
			return busy;
		},
		get error() {
			return error;
		},

		tool(name: string): ToolSpec | undefined {
			return catalog?.tools.find((t) => t.name === name);
		},

		async load(force = false) {
			if (loadingCatalog || (catalog && !force)) return;
			loadingCatalog = true;
			catalogError = null;
			try {
				catalog = await toolboxApi.catalog();
			} catch (e) {
				catalogError = e instanceof Error ? e.message : 'The toolbox could not be loaded';
			} finally {
				loadingCatalog = false;
			}
			void this.loadHistory();
		},

		async loadHistory() {
			try {
				history = await toolboxApi.runs();
			} catch {
				history = [];
			}
		},

		async lookup(q: string, projectId?: string) {
			if (busy) return;
			busy = true;
			error = null;
			stopPolling();
			try {
				const result = await toolboxApi.lookup(q, projectId);
				subject = result;
				runs = result.runs;
				error = result.error;
				for (const run of result.runs) history = [run, ...history.filter((r) => r.id !== run.id)];
				schedule();
			} catch (e) {
				error = e instanceof Error ? e.message : 'The lookup could not be started';
			} finally {
				busy = false;
			}
		},

		async add(tool: string, input: Record<string, unknown>, projectId?: string) {
			try {
				replace(await toolboxApi.run({ tool, input, project_id: projectId }));
				schedule();
			} catch (e) {
				error = e instanceof Error ? e.message : 'The run could not be started';
			}
		},

		show(run: ToolRun) {
			subject = {
				kind: null,
				kind_label: null,
				value: run.label,
				runs: [run],
				offered: [],
				error: null
			};
			runs = [run];
			schedule();
		},

		async clear() {
			stopPolling();
			history = [];
			await toolboxApi.clear();
		},

		reset() {
			stopPolling();
			catalog = null;
			catalogError = null;
			history = [];
			subject = null;
			runs = [];
			busy = false;
			error = null;
		}
	};
}

export const toolbox = createToolboxStore();
