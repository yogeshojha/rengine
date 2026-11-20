import { describe, expect, it } from 'vitest';
import { accessSummary, mayCreateProjects, projectAccess } from './users';

const projects = [
	{ id: 'a', name: 'Acme Retail' },
	{ id: 'b', name: 'Acme Cloud' },
	{ id: 'c', name: 'Bug Bounty' }
];

describe('projectAccess', () => {
	it('opens every project to an administrator', () => {
		expect(projectAccess({ is_superuser: true, project_ids: [] }, projects)).toEqual({
			kind: 'all'
		});
	});

	it('lists a member project in the order of the project list', () => {
		const access = projectAccess({ is_superuser: false, project_ids: ['c', 'a'] }, projects);
		expect(access).toEqual({ kind: 'some', projects: [projects[0], projects[2]] });
	});

	it('reads no project when none is held or the held one is gone', () => {
		expect(projectAccess({ is_superuser: false, project_ids: [] }, projects).kind).toBe('none');
		expect(projectAccess({ is_superuser: false, project_ids: ['z'] }, projects).kind).toBe('none');
		expect(projectAccess({ is_superuser: false }, projects).kind).toBe('none');
	});
});

describe('mayCreateProjects', () => {
	it('allows an administrator and a user granted creation', () => {
		expect(mayCreateProjects({ is_superuser: true })).toBe(true);
		expect(mayCreateProjects({ is_superuser: false, can_create_projects: true })).toBe(true);
	});

	it('refuses a standard user and no user', () => {
		expect(mayCreateProjects({ is_superuser: false, can_create_projects: false })).toBe(false);
		expect(mayCreateProjects({ is_superuser: false })).toBe(false);
		expect(mayCreateProjects(null)).toBe(false);
	});
});

describe('accessSummary', () => {
	it('counts the selection and names the user', () => {
		expect(accessSummary(2, 4, 'priya.n')).toBe(
			'2 of 4 projects. Open sessions of priya.n are signed out on save.'
		);
	});
});
