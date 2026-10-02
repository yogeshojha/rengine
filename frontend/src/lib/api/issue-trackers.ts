import { api } from './client';
import { scopeQuery } from '$lib/utilities/surface-scope';
import type {
	FileSelection,
	FilingPlan,
	FilingResult,
	IssueTracker,
	IssueTrackerTest,
	IssueTrackerWrite,
	RouteWrite,
	TestResult,
	TrackedIssue,
	TrackerOption,
	TrackerRoute
} from '$lib/types/issue-tracker';

const BASE = '/issue-trackers';

export const issueTrackersApi = {
	list(): Promise<IssueTracker[]> {
		return api.get<IssueTracker[]>(BASE);
	},

	create(body: IssueTrackerWrite): Promise<IssueTracker> {
		return api.post<IssueTracker>(BASE, body);
	},

	update(id: string, body: IssueTrackerWrite): Promise<IssueTracker> {
		return api.patch<IssueTracker>(`${BASE}/${id}`, body);
	},

	remove(id: string): Promise<void> {
		return api.delete<void>(`${BASE}/${id}`);
	},

	testConfig(body: IssueTrackerTest): Promise<TestResult> {
		return api.post<TestResult>(`${BASE}/test`, body);
	},

	test(id: string): Promise<TestResult> {
		return api.post<TestResult>(`${BASE}/${id}/test`);
	},

	destinations(id: string, q = ''): Promise<TrackerOption[]> {
		return api.get<TrackerOption[]>(`${BASE}/${id}/destinations?q=${encodeURIComponent(q)}`);
	},

	issueTypes(id: string, destination: string): Promise<TrackerOption[]> {
		return api.get<TrackerOption[]>(
			`${BASE}/${id}/issue-types?destination=${encodeURIComponent(destination)}`
		);
	},

	routes(projectId: string): Promise<TrackerRoute[]> {
		return api.get<TrackerRoute[]>(`${BASE}/routes?project_id=${projectId}`);
	},

	setRoute(body: RouteWrite): Promise<TrackerRoute> {
		return api.put<TrackerRoute>(`${BASE}/routes`, body);
	},

	removeRoute(id: string): Promise<void> {
		return api.delete<void>(`${BASE}/routes/${id}`);
	},

	issues(projectId: string): Promise<TrackedIssue[]> {
		const sp = new URLSearchParams({ project_id: projectId });
		return api.get<TrackedIssue[]>(`${BASE}/issues?${sp.toString()}`);
	},

	plan(projectId: string, scanId: string, body: FileSelection): Promise<FilingPlan> {
		return api.post<FilingPlan>(`${BASE}/issues/plan?${scopeQuery({ projectId, scanId })}`, body);
	},

	file(projectId: string, scanId: string, body: FileSelection): Promise<FilingResult> {
		return api.post<FilingResult>(`${BASE}/issues?${scopeQuery({ projectId, scanId })}`, body);
	},

	retry(id: string): Promise<TrackedIssue> {
		return api.post<TrackedIssue>(`${BASE}/issues/${id}/retry`);
	},

	refresh(id: string): Promise<TrackedIssue> {
		return api.post<TrackedIssue>(`${BASE}/issues/${id}/refresh`);
	},

	unlink(id: string): Promise<void> {
		return api.delete<void>(`${BASE}/issues/${id}`);
	}
};
