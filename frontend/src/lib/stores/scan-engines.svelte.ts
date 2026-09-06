import { scanEnginesApi } from '$lib/api/scan-engines';
import type { ScanEngine, ScanEngineCreate, ScanEngineUpdate } from '$lib/types/scan-engine';

function createScanEnginesStore() {
	let engines = $state<ScanEngine[]>([]);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);
	let fetchedProjectId = $state<string | null>(null);
	let activeEngine = $state<ScanEngine | null>(null);

	return {
		get engines() {
			return engines;
		},
		get isLoading() {
			return isLoading;
		},
		get error() {
			return error;
		},
		get hasFetched() {
			return hasFetched;
		},
		get fetchedProjectId() {
			return fetchedProjectId;
		},
		get activeEngine() {
			return activeEngine;
		},

		async fetchEngines(projectId: string) {
			if (isLoading) return;
			isLoading = true;
			error = null;
			try {
				engines = await scanEnginesApi.list(projectId);
				hasFetched = true;
				fetchedProjectId = projectId;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan engines could not be loaded';
			} finally {
				isLoading = false;
			}
		},

		async createEngine(projectId: string, data: ScanEngineCreate): Promise<ScanEngine | null> {
			error = null;
			try {
				const created = await scanEnginesApi.create(projectId, data);
				engines = [...engines, created];
				return created;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan engine could not be created';
				return null;
			}
		},

		async updateEngine(
			id: string,
			projectId: string,
			data: ScanEngineUpdate
		): Promise<ScanEngine | null> {
			error = null;
			try {
				const updated = await scanEnginesApi.update(id, projectId, data);
				engines = engines.map((e) => (e.id === id ? updated : e));
				if (activeEngine?.id === id) {
					activeEngine = updated;
				}
				return updated;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan engine could not be updated';
				return null;
			}
		},

		async deleteEngine(id: string, projectId?: string): Promise<boolean> {
			error = null;
			try {
				const pid = projectId ?? engines.find((e) => e.id === id)?.project_id ?? '';
				await scanEnginesApi.delete(id, pid);
				engines = engines.filter((e) => e.id !== id);
				if (activeEngine?.id === id) {
					activeEngine = null;
				}
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan engine could not be deleted';
				return false;
			}
		},

		async duplicateEngine(id: string, projectId: string): Promise<ScanEngine | null> {
			error = null;
			try {
				const duplicate = await scanEnginesApi.duplicate(id, projectId);
				engines = [...engines, duplicate];
				return duplicate;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan engine could not be duplicated';
				return null;
			}
		},

		setActiveEngine(engine: ScanEngine | null) {
			activeEngine = engine;
		},

		async exportYaml(id: string, projectId: string): Promise<string | null> {
			error = null;
			try {
				const res = await scanEnginesApi.exportYaml(id, projectId);
				return res.yaml;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan engine could not be exported';
				return null;
			}
		},

		async importYaml(projectId: string, yaml: string): Promise<ScanEngine | null> {
			error = null;
			try {
				const imported = await scanEnginesApi.importYaml(projectId, yaml);
				engines = [...engines, imported];
				return imported;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Scan engine could not be imported';
				return null;
			}
		},

		clear() {
			engines = [];
			activeEngine = null;
			error = null;
			hasFetched = false;
			fetchedProjectId = null;
		}
	};
}

export const scanEnginesStore = createScanEnginesStore();
