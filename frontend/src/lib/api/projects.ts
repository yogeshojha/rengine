import { api } from './client';
import type { Project, ProjectCreate } from '$lib/types/project';

export const projectsApi = {
	list: (): Promise<Project[]> => api.get<Project[]>('/projects'),

	create: (data: ProjectCreate): Promise<Project> => {
		return api.post<Project>('/projects', data);
	}
};
