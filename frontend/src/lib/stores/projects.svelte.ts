import { projectsApi } from '$lib/api/projects';
import type { Project } from '$lib/types/project';

function createProjectsStore() {
	let projects = $state<Project[]>([]);
	let activeProject = $state<Project | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	return {
		get projects() { return projects; },
		get activeProject() { return activeProject; },
		get isLoading() { return isLoading; },
		get error() { return error; },
		get hasFetched() { return hasFetched; },

		async fetchProjects() {
			if (hasFetched || isLoading) return;

			isLoading = true;
			error = null;

			try {
				projects = await projectsApi.list();
				hasFetched = true;

				if (!activeProject && projects.length > 0) {
					activeProject = projects[0];
				}
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to fetch projects';
			} finally {
				isLoading = false;
			}
		},

		async refresh() {
			hasFetched = false;
			projects = [];
			await this.fetchProjects();
		},

		setActiveProject(project: Project) {
			activeProject = project;
			localStorage.setItem('activeProjectSlug', project.slug);
		},

		async createProject(name: string): Promise<Project | null> {
			error = null;

			try {
				const newProject = await projectsApi.create({ name });
				projects = [newProject, ...projects];
				return newProject;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to create project';
				return null;
			}
		},

		async deleteProject(slug: string): Promise<boolean> {
			try {
				await projectsApi.delete(slug);
				projects = projects.filter((p) => p.slug !== slug);

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
			hasFetched = false;
		},
	};
}

export const projectsStore = createProjectsStore();
