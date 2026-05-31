export interface Project {
	id: string;
	name: string;
	slug: string;
	is_active: boolean;
	created_at: string;
	created_by: string;
}

export interface ProjectCreate {
	name: string;
}
