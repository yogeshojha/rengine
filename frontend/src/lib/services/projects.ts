export interface Project {
	id: string;
	name: string;
	icon: string;
	description?: string;
	targets_count?: number;
	created_at: string;
}

// Simulated network delay
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock data
const mockProjects: Project[] = [
	{
		id: 'proj_1',
		name: 'ACME Corp',
		icon: 'Building2',
		description: 'Main corporate infrastructure',
		targets_count: 12,
		created_at: '2024-01-15T10:00:00Z'
	},
	{
		id: 'proj_2',
		name: 'Client Alpha',
		icon: 'Shield',
		description: 'Penetration testing engagement',
		targets_count: 5,
		created_at: '2024-02-20T14:30:00Z'
	},
	{
		id: 'proj_3',
		name: 'Bug Bounty',
		icon: 'Bug',
		description: 'Public bug bounty targets',
		targets_count: 28,
		created_at: '2024-03-01T09:00:00Z'
	}
];

export async function fetchProjects(): Promise<Project[]> {
	await delay(300);
	return mockProjects;
}

export async function createProject(
	data: Omit<Project, 'id' | 'created_at' | 'targets_count'>
): Promise<Project> {
	await delay(200);
	const newProject: Project = {
		...data,
		id: `proj_${Date.now()}`,
		targets_count: 0,
		created_at: new Date().toISOString()
	};
	mockProjects.push(newProject);
	return newProject;
}

export async function deleteProject(id: string): Promise<void> {
	await delay(200);
	const index = mockProjects.findIndex((p) => p.id === id);
	if (index > -1) {
		mockProjects.splice(index, 1);
	}
}