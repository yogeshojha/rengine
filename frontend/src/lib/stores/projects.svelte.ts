import { projectsApi } from '$lib/api/projects';
import type { Project } from '$lib/types/project';
import { toast } from 'svelte-sonner';

function getStoredActiveProjectSlug(): string | null {
	if (typeof window === 'undefined') return null;
	return localStorage.getItem('activeProjectSlug');
}

function createProjectsStore() {
	let projects = $state<Project[]>([]);
	let activeProject = $state<Project | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	return {
		get projects() {
			return projects;
		},
		get activeProject() {
			return activeProject;
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

		getCurrentProject(): Project | null {
			return activeProject;
		},

		async fetchProjects() {
			if (hasFetched || isLoading) return;

			isLoading = true;
			error = null;

			try {
				projects = await projectsApi.list();
				hasFetched = true;

				const storedSlug = getStoredActiveProjectSlug();

				if (storedSlug) {
					const restoredProject = projects.find((p) => p.slug === storedSlug);
					if (restoredProject) {
						activeProject = restoredProject;
					} else {
						activeProject = projects.length > 0 ? projects[0] : null;
					}
				} else if (projects.length > 0) {
					activeProject = projects[0];
				}
			} catch (e) {
				error = e instanceof Error ? e.message : 'Projects could not be loaded';
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
			const previousProject = activeProject;
			activeProject = project;
			if (typeof window === 'undefined') return;
			localStorage.setItem('activeProjectSlug', project.slug);

			if (previousProject && previousProject.slug !== project.slug) {
				toast.info(`Switched to project "${project.name}"`);
			}
		},

		async createProject(name: string): Promise<Project | null> {
			error = null;

			try {
				const newProject = await projectsApi.create({ name });
				projects = [newProject, ...projects];
				return newProject;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Project could not be created';
				return null;
			}
		},

		async deleteProject(slug: string): Promise<boolean> {
			try {
				await projectsApi.delete(slug);
				projects = projects.filter((p) => p.slug !== slug);

				if (activeProject?.slug === slug) {
					activeProject = projects[0] || null;

					if (activeProject) {
						localStorage.setItem('activeProjectSlug', activeProject.slug);
					} else {
						localStorage.removeItem('activeProjectSlug');
					}
				}
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Project could not be deleted';
				return false;
			}
		},

		clear() {
			projects = [];
			activeProject = null;
			error = null;
			hasFetched = false;
			if (typeof window !== 'undefined') {
				localStorage.removeItem('activeProjectSlug');
			}
		}
	};
}

export const projectsStore = createProjectsStore();
