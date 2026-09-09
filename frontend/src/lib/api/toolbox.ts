import { api } from './client';
import type { ToolboxCatalog, ToolRun, ToolRunRequest } from '$lib/types/toolbox';

export const toolboxApi = {
	catalog: () => api.get<ToolboxCatalog>('/toolbox/catalog'),
	run: (body: ToolRunRequest) => api.post<ToolRun>('/toolbox/run', body),
	runs: () => api.get<ToolRun[]>('/toolbox/runs'),
	get: (id: string) => api.get<ToolRun>(`/toolbox/runs/${id}`),
	clear: () => api.delete<void>('/toolbox/runs')
};
