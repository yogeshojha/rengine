import { issueTrackersApi } from '$lib/api/issue-trackers';
import { MAX_LISTED } from '$lib/config/issue-trackers';
import type { IssueTracker, TrackedIssue, TrackerRoute } from '$lib/types/issue-tracker';

function createIssueTrackersStore() {
	let trackers = $state<IssueTracker[]>([]);
	let loaded = $state(false);
	let pending: Promise<void> | null = null;
	let routes = $state<TrackerRoute[]>([]);
	let issues = $state<TrackedIssue[]>([]);
	let issuesLoading = $state(false);
	let error = $state<string | null>(null);
	let issuesError = $state<string | null>(null);
	let fetchedProjectId = $state<string | null>(null);
	let projectReq = 0;
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const read = new Set<string>();

	function message(e: unknown, fallback: string) {
		return e instanceof Error ? e.message : fallback;
	}

	return {
		get trackers() {
			return trackers;
		},
		get active() {
			return trackers.filter((t) => t.is_active);
		},
		get loaded() {
			return loaded;
		},
		get routes() {
			return routes;
		},
		get issues() {
			return issues;
		},
		get issuesLoading() {
			return issuesLoading;
		},
		get error() {
			return error;
		},
		get issuesError() {
			return issuesError;
		},
		get issuesCapped() {
			return issues.length >= MAX_LISTED;
		},

		async load(force = false) {
			if (loaded && !force) return;
			pending ??= issueTrackersApi
				.list()
				.then((rows) => {
					trackers = rows;
					loaded = true;
					error = null;
				})
				.catch((e) => {
					error = message(e, 'Issue trackers not loaded');
				})
				.finally(() => {
					pending = null;
				});
			return pending;
		},

		async loadProject(projectId: string, force = false) {
			if (!force && fetchedProjectId === projectId) return;
			const my = ++projectReq;
			if (fetchedProjectId !== projectId) {
				routes = [];
				issues = [];
			}
			issuesLoading = true;
			try {
				const [r, i] = await Promise.all([
					issueTrackersApi.routes(projectId),
					issueTrackersApi.issues(projectId)
				]);
				if (my !== projectReq) return;
				routes = r;
				issues = i;
				fetchedProjectId = projectId;
				issuesError = null;
			} catch (e) {
				if (my === projectReq) issuesError = message(e, 'Issues not loaded');
			} finally {
				if (my === projectReq) issuesLoading = false;
			}
		},

		firstRead(issueId: string): boolean {
			if (read.has(issueId)) return false;
			read.add(issueId);
			return true;
		},

		forgetRead(issueId: string) {
			read.delete(issueId);
		},

		upsert(tracker: IssueTracker) {
			const at = trackers.findIndex((t) => t.id === tracker.id);
			if (at >= 0) trackers[at] = tracker;
			else trackers = [...trackers, tracker].sort((a, b) => a.name.localeCompare(b.name));
		},

		drop(id: string) {
			trackers = trackers.filter((t) => t.id !== id);
			routes = routes.filter((r) => r.tracker_id !== id);
			issues = issues.filter((i) => i.tracker_id !== id);
		},

		upsertRoute(route: TrackerRoute) {
			const at = routes.findIndex((r) => r.id === route.id);
			if (at >= 0) routes[at] = route;
			else routes = [...routes, route];
		},

		dropRoute(id: string) {
			routes = routes.filter((r) => r.id !== id);
		},

		upsertIssue(issue: TrackedIssue) {
			const at = issues.findIndex((i) => i.id === issue.id);
			if (at >= 0) issues[at] = issue;
			else issues = [issue, ...issues];
		},

		dropIssue(id: string) {
			issues = issues.filter((i) => i.id !== id);
		},

		reset() {
			trackers = [];
			loaded = false;
			pending = null;
			routes = [];
			issues = [];
			issuesLoading = false;
			error = null;
			issuesError = null;
			fetchedProjectId = null;
			projectReq += 1;
			read.clear();
		}
	};
}

export const issueTrackers = createIssueTrackersStore();
