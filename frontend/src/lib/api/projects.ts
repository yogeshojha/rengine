import { api } from './client';
import type { Project, ProjectCreate } from '$lib/types/project';

export const projectsApi = {
    list: (includeInactive = false): Promise<Project[]> => {
        const params = includeInactive ? '?include_inactive=true' : '';
        return api.get<Project[]>(`/projects${params}`);
    },

    get: (slug: string): Promise<Project> => {
        return api.get<Project>(`/projects/${slug}`);
    },

    create: (data: ProjectCreate): Promise<Project> => {
        return api.post<Project>('/projects', data);
    },

    delete: (slug: string): Promise<void> => {
        return api.delete(`/projects/${slug}`);
    },
};
