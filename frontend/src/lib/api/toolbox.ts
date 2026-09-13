import { LONG_REQUEST_TIMEOUT_MS, api } from './client';
import type { ToolboxCatalog, ToolRun, ToolRunRequest } from '$lib/types/toolbox';

export const toolboxApi = {
	catalog: () => api.get<ToolboxCatalog>('/toolbox/catalog'),
	run: (body: ToolRunRequest) => api.post<ToolRun>('/toolbox/run', body, LONG_REQUEST_TIMEOUT_MS),
	runs: () => api.get<ToolRun[]>('/toolbox/runs'),
	get: (id: string) => api.get<ToolRun>(`/toolbox/runs/${id}`),
	clear: () => api.delete<void>('/toolbox/runs')
};
