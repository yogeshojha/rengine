import { fetchProjects, createProject, type Project } from '$lib/services/projects';

const ACTIVE_PROJECT_KEY = 'rengine_active_project';

function createProjectsStore() {
	let projects = $state<Project[]>([]);
	let activeProject = $state<Project | null>(null);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let isInitialized = $state(false);

	function loadPersistedProject() {
		if (typeof window === 'undefined') return null;
		const stored = localStorage.getItem(ACTIVE_PROJECT_KEY);
		return stored ? JSON.parse(stored) : null;
	}

	function persistActiveProject(project: Project | null) {
		if (typeof window === 'undefined') return;
		if (project) {
			localStorage.setItem(ACTIVE_PROJECT_KEY, JSON.stringify(project));
		} else {
			localStorage.removeItem(ACTIVE_PROJECT_KEY);
		}
	}

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
		get isInitialized() {
			return isInitialized;
		},

		async init() {
			if (isInitialized) return;

			isLoading = true;
			error = null;

			try {
				projects = await fetchProjects();

				const persisted = loadPersistedProject();
				if (persisted) {
					const found = projects.find((p) => p.id === persisted.id);
					activeProject = found || projects[0] || null;
				} else {
					activeProject = projects[0] || null;
				}

				if (activeProject) {
					persistActiveProject(activeProject);
				}

				isInitialized = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to load projects';
			} finally {
				isLoading = false;
			}
		},

		setActiveProject(project: Project) {
			activeProject = project;
			persistActiveProject(project);
		},

		async addProject(data: Omit<Project, 'id' | 'created_at' | 'targets_count'>) {
			try {
				const newProject = await createProject(data);
				projects = [...projects, newProject];
				return newProject;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to create project';
				throw e;
			}
		},

		async refresh() {
			isLoading = true;
			try {
				projects = await fetchProjects();
				if (activeProject && !projects.find((p) => p.id === activeProject!.id)) {
					activeProject = projects[0] || null;
					persistActiveProject(activeProject);
				}
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to refresh projects';
			} finally {
				isLoading = false;
			}
		}
	};
}

export const projectsStore = createProjectsStore();