export const ROLE_LABELS = {
	admin: 'Administrator',
	member: 'Standard user'
} as const;

export const PROJECT_ACCESS_LABELS = {
	title: 'Project access',
	all: 'All projects',
	none: 'No project',
	create: 'Can create projects'
} as const;

export const NO_PROJECT_ACCESS = {
	title: 'No project access',
	description: 'An administrator adds users to projects.'
} as const;

export function roleLabel(isSuperuser: boolean): string {
	return isSuperuser ? ROLE_LABELS.admin : ROLE_LABELS.member;
}

interface ProjectHolder {
	is_superuser: boolean;
	can_create_projects?: boolean;
	project_ids?: readonly string[];
}

interface NamedProject {
	id: string;
	name: string;
}

export type ProjectAccess<P extends NamedProject = NamedProject> =
	| { kind: 'all' }
	| { kind: 'none' }
	| { kind: 'some'; projects: P[] };

/** The projects a user opens, in the order of the project list. */
export function projectAccess<P extends NamedProject>(
	user: ProjectHolder,
	projects: readonly P[]
): ProjectAccess<P> {
	if (user.is_superuser) return { kind: 'all' };
	const held = new Set(user.project_ids ?? []);
	const open = projects.filter((p) => held.has(p.id));
	return open.length ? { kind: 'some', projects: open } : { kind: 'none' };
}

export function mayCreateProjects(user: ProjectHolder | null | undefined): boolean {
	return !!user && (user.is_superuser || !!user.can_create_projects);
}

export function accessSummary(selected: number, total: number, username: string): string {
	return `${selected} of ${total} projects. Open sessions of ${username} are signed out on save.`;
}
