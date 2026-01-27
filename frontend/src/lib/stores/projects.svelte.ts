import { projectsApi } from '$lib/api/projects';
import type { Project } from '$lib/types/project';

function createProjectsStore() {
    let projects = $state<Project[]>([]);
    let activeProject = $state<Project | null>(null);
    let isLoading = $state(false);
    let error = $state<string | null>(null);

    return {
        get projects() { return projects; },
        get activeProject() { return activeProject; },
        get isLoading() { return isLoading; },
        get error() { return error; },

        async fetchProjects() {
            if (projects.length > 0) return;

            isLoading = true;
            error = null;

            try {
                projects = await projectsApi.list();

                if (!activeProject && projects.length > 0) {
                    activeProject = projects[0];
                }
            } catch (e) {
                error = e instanceof Error ? e.message : 'Failed to fetch projects';
                console.error('Failed to fetch projects:', e);
            } finally {
                isLoading = false;
            }
        },

        async refresh() {
            projects = []; // Clear cache
            await this.fetchProjects();
        },

        setActiveProject(project: Project) {
            activeProject = project;
            localStorage.setItem('activeProjectSlug', project.slug);
        },

        async createProject(name: string): Promise<Project | null> {
            try {
                const newProject = await projectsApi.create({ name });
                projects = [...projects, newProject];
                return newProject;
            } catch (e) {
                error = e instanceof Error ? e.message : 'Failed to create project';
                return null;
            }
        },

        async deleteProject(slug: string): Promise<boolean> {
            try {
                await projectsApi.delete(slug);
                projects = projects.filter(p => p.slug !== slug);

                // If deleted project was active, switch to first available
                if (activeProject?.slug === slug) {
                    activeProject = projects[0] || null;
                }
                return true;
            } catch (e) {
                error = e instanceof Error ? e.message : 'Failed to delete project';
                return false;
            }
        },

        clear() {
            projects = [];
            activeProject = null;
            error = null;
        }
    };
}

export const projectsStore = createProjectsStore();
