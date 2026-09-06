import { reportsApi } from '$lib/api/reports';
import { isLive } from '$lib/config/reports';
import type { Report, ReportCreate, ReportTemplate } from '$lib/types/report';
import { toast } from 'svelte-sonner';

const POLL_MS = 1800;

function createReportsStore() {
	let reports = $state<Report[]>([]);
	let templates = $state<ReportTemplate[]>([]);
	let isLoading = $state(false);
	let templatesLoading = $state(false);
	let fetchedProjectId = $state<string | null>(null);
	let templatesProjectId = $state<string | null>(null);
	let timer: ReturnType<typeof setTimeout> | null = null;

	function schedule(projectId: string) {
		if (timer) clearTimeout(timer);
		if (!reports.some((r) => isLive(r.status))) return;
		timer = setTimeout(() => {
			void refreshLive(projectId);
		}, POLL_MS);
	}

	async function refreshLive(projectId: string) {
		const live = reports.filter((r) => isLive(r.status));
		if (!live.length) return;
		try {
			const updated = await Promise.all(
				live.map((r) => reportsApi.get(projectId, r.id).catch(() => r))
			);
			const map = new Map(updated.map((r) => [r.id, r]));
			reports = reports.map((r) => map.get(r.id) ?? r);
		} finally {
			schedule(projectId);
		}
	}

	return {
		get reports() {
			return reports;
		},
		get templates() {
			return templates;
		},
		get isLoading() {
			return isLoading;
		},
		get templatesLoading() {
			return templatesLoading;
		},
		get liveCount() {
			return reports.filter((r) => isLive(r.status)).length;
		},

		for(opts: { scanId?: string; targetId?: string }): Report[] {
			return reports.filter(
				(r) =>
					(!opts.scanId || r.scan_id === opts.scanId) &&
					(!opts.targetId || r.target_id === opts.targetId)
			);
		},

		async fetch(projectId: string, force = false) {
			if (isLoading || (fetchedProjectId === projectId && !force)) return;
			isLoading = true;
			try {
				reports = await reportsApi.list(projectId);
				fetchedProjectId = projectId;
				schedule(projectId);
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Reports could not be loaded');
			} finally {
				isLoading = false;
			}
		},

		async fetchTemplates(projectId: string, force = false) {
			if (templatesLoading || (templatesProjectId === projectId && !force)) return;
			templatesLoading = true;
			try {
				templates = await reportsApi.templates(projectId);
				templatesProjectId = projectId;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Report templates could not be loaded');
			} finally {
				templatesLoading = false;
			}
		},

		async create(projectId: string, body: ReportCreate): Promise<Report | null> {
			try {
				const report = await reportsApi.create(projectId, body);
				reports = [report, ...reports];
				schedule(projectId);
				return report;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Report could not be started');
				return null;
			}
		},

		async retry(projectId: string, id: string): Promise<boolean> {
			try {
				const report = await reportsApi.retry(projectId, id);
				reports = reports.map((r) => (r.id === id ? report : r));
				schedule(projectId);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Report could not be restarted');
				return false;
			}
		},

		async remove(projectId: string, id: string): Promise<boolean> {
			try {
				await reportsApi.remove(projectId, id);
				reports = reports.filter((r) => r.id !== id);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Report could not be deleted');
				return false;
			}
		},

		async saveTemplate(projectId: string, id: string, body: unknown): Promise<boolean> {
			try {
				const updated = await reportsApi.updateTemplate(projectId, id, body);
				templates = templates.map((t) => (t.id === id ? updated : t));
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Template could not be saved');
				return false;
			}
		},

		async createTemplate(projectId: string, body: unknown): Promise<ReportTemplate | null> {
			try {
				const created = await reportsApi.createTemplate(projectId, body);
				templates = [...templates, created];
				return created;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Template could not be created');
				return null;
			}
		},

		async removeTemplate(projectId: string, id: string): Promise<boolean> {
			try {
				await reportsApi.deleteTemplate(projectId, id);
				templates = templates.filter((t) => t.id !== id);
				return true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Template could not be deleted');
				return false;
			}
		},

		reset() {
			if (timer) clearTimeout(timer);
			timer = null;
			reports = [];
			templates = [];
			isLoading = false;
			templatesLoading = false;
			fetchedProjectId = null;
			templatesProjectId = null;
		}
	};
}

export const reports = createReportsStore();
