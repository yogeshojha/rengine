import { targetsApi } from '$lib/api/targets';
import { organizationsApi, type Organization } from '$lib/api/organizations';
import { tagsApi, type Tag } from '$lib/api/tags';
import { TargetType, type Target } from '$lib/types/target';
import { TaskStatus } from '$lib/types/task-status';
import type { TargetCounts } from '$lib/types/pagination';
import type { SignalFilter, SortDir, SortKey, TargetSummary } from '$lib/utilities/target-signals';

interface TargetFilters {
	projectSlug?: string;
	searchQuery: string;
	activeTab: string;
	selectedOrganizations: string[];
	selectedTags: string[];
	signalFilter: SignalFilter | null;
	sortKey: SortKey;
	sortDir: SortDir;
}

interface PaginationState {
	currentPage: number;
	pageSize: number;
	totalItems: number;
	totalPages: number;
}

function createTargetsStore() {
	let targets = $state<Target[]>([]);
	let organizations = $state<Organization[]>([]);
	let tags = $state<Tag[]>([]);

	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let hasFetched = $state(false);

	let filters = $state<TargetFilters>({
		searchQuery: '',
		activeTab: 'all',
		selectedOrganizations: [],
		selectedTags: [],
		signalFilter: null,
		sortKey: 'updated',
		sortDir: 'desc'
	});

	let pagination = $state<PaginationState>({
		currentPage: 1,
		pageSize: 20,
		totalItems: 0,
		totalPages: 0
	});

	let counts = $state<TargetCounts>({
		all: 0,
		domain: 0,
		ip: 0,
		ip_range: 0,
		asn: 0,
		url: 0
	});

	// KPI counts from /targets/stats; filtering/sort/signal are server-side
	let signalSummary = $state<TargetSummary>({
		total: 0,
		expiring: 0,
		attention: 0,
		awaiting: 0,
		enriched: 0
	});

	let searchDebounce: ReturnType<typeof setTimeout> | undefined;

	let hasActiveFilters = $derived(
		filters.searchQuery.trim() !== '' ||
			filters.selectedOrganizations.length > 0 ||
			filters.selectedTags.length > 0 ||
			filters.signalFilter !== null
	);

	return {
		get targets() {
			return targets;
		},
		get filteredTargets() {
			// already server-filtered/sorted
			return targets;
		},
		get signalSummary() {
			return signalSummary;
		},
		get organizations() {
			return organizations;
		},
		get tags() {
			return tags;
		},
		get counts() {
			return counts;
		},
		get filters() {
			return filters;
		},
		get pagination() {
			return pagination;
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
		get hasActiveFilters() {
			return hasActiveFilters;
		},

		async fetchAll(projectSlug: string, page?: number, force: boolean = false) {
			if (isLoading && !force) return;

			if (!force && hasFetched && projectSlug === filters.projectSlug && page === undefined) {
				return;
			}

			const projectChanged = projectSlug !== filters.projectSlug;
			if (projectChanged) {
				targets = [];
				organizations = [];
				tags = [];
				hasFetched = false;
				pagination.currentPage = 1;
			}

			if (page !== undefined) {
				pagination.currentPage = page;
			}

			isLoading = true;
			error = null;
			filters.projectSlug = projectSlug;

			try {
				const targetType =
					filters.activeTab !== 'all' ? (filters.activeTab as TargetType) : undefined;

				// shared by list + stats (no signal/sort)
				const baseFilters = {
					project_slug: projectSlug,
					search: filters.searchQuery || undefined,
					organization_ids: filters.selectedOrganizations.length
						? filters.selectedOrganizations
						: undefined,
					tag_ids: filters.selectedTags.length ? filters.selectedTags : undefined,
					target_type: targetType
				};

				const shouldFetchOrgsAndTags = !hasFetched || projectChanged;

				const promises: Promise<any>[] = [
					targetsApi.list({
						...baseFilters,
						signal: filters.signalFilter,
						sort_by: filters.sortKey,
						sort_dir: filters.sortDir,
						page: pagination.currentPage,
						size: pagination.pageSize === -1 ? undefined : pagination.pageSize
					}),
					targetsApi.getStats(baseFilters)
				];

				if (shouldFetchOrgsAndTags) {
					promises.push(
						organizationsApi.list({ project_slug: projectSlug }),
						tagsApi.list({ project_slug: projectSlug }),
						targetsApi.getCounts(projectSlug)
					);
				}

				const results = await Promise.all(promises);
				const targetsResponse = results[0];

				targets = targetsResponse.items;
				pagination.totalItems = targetsResponse.total;
				pagination.totalPages = targetsResponse.pages;
				signalSummary = results[1];

				if (shouldFetchOrgsAndTags) {
					organizations = results[2];
					tags = results[3];
					counts = results[4];
				}

				hasFetched = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to fetch data';
			} finally {
				isLoading = false;
			}
		},

		// re-fetch after a filter/sort change, back to page 1
		async reload() {
			if (!filters.projectSlug) return;
			pagination.currentPage = 1;
			await this.fetchAll(filters.projectSlug, 1, true);
		},

		async refresh() {
			if (!filters.projectSlug) return;
			await Promise.all([
				this.fetchAll(filters.projectSlug, pagination.currentPage, true),
				this.refreshCounts()
			]);
		},

		async refreshCounts() {
			if (!filters.projectSlug) return;
			try {
				counts = await targetsApi.getCounts(filters.projectSlug);
			} catch (e) {
				// counts are non-critical, fail silently
			}
		},

		setSearchQuery(query: string) {
			filters.searchQuery = query;
			// debounce server round-trip
			if (searchDebounce) clearTimeout(searchDebounce);
			searchDebounce = setTimeout(() => {
				this.reload();
			}, 300);
		},

		async setActiveTab(tab: string) {
			filters.activeTab = tab;
			await this.reload();
		},

		toggleOrganization(orgId: string) {
			const index = filters.selectedOrganizations.indexOf(orgId);
			if (index === -1) {
				filters.selectedOrganizations = [...filters.selectedOrganizations, orgId];
			} else {
				filters.selectedOrganizations = filters.selectedOrganizations.filter((id) => id !== orgId);
			}
			this.reload();
		},

		toggleTag(tagId: string) {
			const index = filters.selectedTags.indexOf(tagId);
			if (index === -1) {
				filters.selectedTags = [...filters.selectedTags, tagId];
			} else {
				filters.selectedTags = filters.selectedTags.filter((id) => id !== tagId);
			}
			this.reload();
		},

		toggleSignalFilter(signal: SignalFilter) {
			filters.signalFilter = filters.signalFilter === signal ? null : signal;
			this.reload();
		},

		setSignalFilter(signal: SignalFilter | null) {
			filters.signalFilter = signal;
			this.reload();
		},

		setSort(key: SortKey, dir?: SortDir) {
			if (dir) {
				filters.sortKey = key;
				filters.sortDir = dir;
			} else if (filters.sortKey === key) {
				// Same key → toggle direction.
				filters.sortDir = filters.sortDir === 'asc' ? 'desc' : 'asc';
			} else {
				filters.sortKey = key;
				// Names sort A→Z, everything else most-relevant-first.
				filters.sortDir = key === 'name' || key === 'expiry' ? 'asc' : 'desc';
			}
			this.reload();
		},

		clearFilters() {
			filters.searchQuery = '';
			filters.selectedOrganizations = [];
			filters.selectedTags = [];
			filters.signalFilter = null;
			this.reload();
		},

		async setPage(page: number) {
			if (!filters.projectSlug) return;
			await this.fetchAll(filters.projectSlug, page, true);
		},

		async setPageSize(size: number) {
			pagination.pageSize = size;
			pagination.currentPage = 1;
			if (filters.projectSlug) {
				await this.fetchAll(filters.projectSlug, 1, true);
			}
		},

		async createTarget(data: {
			target_value: string;
			display_name?: string;
			project_slug: string;
			organization_names?: string[];
			tag_names?: string[];
		}): Promise<Target | null> {
			error = null;
			try {
				const newTarget = await targetsApi.create(data);
				await this.refresh();
				return newTarget;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to create target';
				return null;
			}
		},

		async updateTarget(
			targetId: string,
			data: {
				display_name?: string | null;
				organization_names?: string[] | null;
				tag_names?: string[] | null;
			}
		): Promise<Target | null> {
			error = null;
			try {
				const updatedTarget = await targetsApi.update(targetId, data);
				targets = targets.map((t) => (t.id === targetId ? updatedTarget : t));
				return updatedTarget;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to update target';
				return null;
			}
		},

		optimisticUpdateTarget(targetId: string, patch: Partial<Target>) {
			targets = targets.map((t) => (t.id === targetId ? { ...t, ...patch } : t));
		},

		async getMatchingIds(): Promise<string[]> {
			if (!filters.projectSlug) return [];
			const targetType =
				filters.activeTab !== 'all' ? (filters.activeTab as TargetType) : undefined;
			return targetsApi.getMatchingIds({
				project_slug: filters.projectSlug,
				search: filters.searchQuery || undefined,
				organization_ids: filters.selectedOrganizations.length
					? filters.selectedOrganizations
					: undefined,
				tag_ids: filters.selectedTags.length ? filters.selectedTags : undefined,
				target_type: targetType,
				signal: filters.signalFilter
			});
		},

		async bulkEnrich(ids: string[], kind: 'whois' | 'dns' | 'bgp'): Promise<number> {
			const res = await targetsApi.bulkEnrich(ids, kind);
			const set = new Set(ids);
			targets = targets.map((t) => {
				if (!set.has(t.id)) return t;
				if (kind === 'whois') return { ...t, whois_status: TaskStatus.PENDING };
				if (kind === 'dns') return { ...t, dns_status: TaskStatus.PENDING };
				return { ...t, bgp_status: TaskStatus.PENDING };
			});
			return res.queued;
		},

		async bulkAddTags(ids: string[], tagNames: string[]): Promise<number> {
			const res = await targetsApi.bulkAddTags(ids, tagNames);
			await this.refresh();
			return res.updated;
		},

		async bulkAddOrganizations(ids: string[], orgNames: string[]): Promise<number> {
			const res = await targetsApi.bulkAddOrganizations(ids, orgNames);
			await this.refresh();
			return res.updated;
		},

		async deleteTarget(targetId: string): Promise<boolean> {
			try {
				await targetsApi.delete(targetId);
				await this.refresh();
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to delete target';
				return false;
			}
		},

		async fetchTags() {
			if (!filters.projectSlug) return;
			try {
				tags = await tagsApi.list({ project_slug: filters.projectSlug });
			} catch {
				// non critical
			}
		},

		async fetchOrganizations() {
			if (!filters.projectSlug) return;
			try {
				organizations = await organizationsApi.list({ project_slug: filters.projectSlug });
			} catch {
				// non critical
			}
		},

		clear() {
			targets = [];
			organizations = [];
			tags = [];
			counts = {
				all: 0,
				domain: 0,
				ip: 0,
				ip_range: 0,
				asn: 0,
				url: 0
			};
			filters = {
				searchQuery: '',
				activeTab: 'all',
				selectedOrganizations: [],
				selectedTags: [],
				signalFilter: null,
				sortKey: 'updated',
				sortDir: 'desc'
			};
			pagination = {
				currentPage: 1,
				pageSize: 50,
				totalItems: 0,
				totalPages: 0
			};
			error = null;
			hasFetched = false;
		}
	};
}

export const targetsStore = createTargetsStore();
