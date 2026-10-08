import { targetsApi } from '$lib/api/targets';
import {
	organizationsApi,
	type Organization,
	type OrganizationUpdate
} from '$lib/api/organizations';
import { tagsApi, type Tag, type TagUpdate } from '$lib/api/tags';
import { TargetType, type EnrichmentKind, type Target } from '$lib/types/target';
import { TaskStatus } from '$lib/types/task-status';
import type { PaginatedResponse, TargetCounts } from '$lib/types/pagination';
import {
	EMPTY_TARGET_SUMMARY,
	type SignalFilter,
	type SortDir,
	type SortKey,
	type TargetSummary
} from '$lib/utilities/target-signals';
import { SvelteURLSearchParams } from 'svelte/reactivity';
import { scansStore } from '$lib/stores/scans.svelte';
import { dashboardStore } from '$lib/stores/dashboard.svelte';

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
	let organizationsSlug: string | undefined;
	let tagsSlug: string | undefined;

	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let loadError = $state<string | null>(null);
	let hasFetched = $state(false);
	let summaryLoaded = $state(false);
	let countsLoaded = $state(false);

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

	let signalSummary = $state<TargetSummary>({ ...EMPTY_TARGET_SUMMARY });

	let searchDebounce: ReturnType<typeof setTimeout> | undefined;
	let seq = 0;

	const hasActiveFilters = $derived(
		filters.searchQuery.trim() !== '' ||
			filters.selectedOrganizations.length > 0 ||
			filters.selectedTags.length > 0 ||
			filters.signalFilter !== null
	);

	const organizationItems = $derived(organizations.map((o) => ({ id: o.id, label: o.name })));
	const tagItems = $derived(tags.map((t) => ({ id: t.id, label: t.name, color: t.color })));

	function scopeFilters(projectSlug: string) {
		return {
			project_slug: projectSlug,
			search: filters.searchQuery || undefined,
			organization_ids: filters.selectedOrganizations.length
				? filters.selectedOrganizations
				: undefined,
			tag_ids: filters.selectedTags.length ? filters.selectedTags : undefined,
			target_type: filters.activeTab !== 'all' ? (filters.activeTab as TargetType) : undefined
		};
	}

	function countFilters(projectSlug: string) {
		return {
			...scopeFilters(projectSlug),
			target_type: undefined,
			signal: filters.signalFilter
		};
	}

	return {
		get targets() {
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
		get organizationItems() {
			return organizationItems;
		},
		get tagItems() {
			return tagItems;
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
		/** Why the list did not load; mutations report through `error`. */
		get loadError() {
			return loadError;
		},
		get hasFetched() {
			return hasFetched;
		},
		/** The signal strip numbers are from the server, not the empty default. */
		get summaryLoaded() {
			return summaryLoaded;
		},
		/** The type tab counts are from the server, not the empty default. */
		get countsLoaded() {
			return countsLoaded;
		},
		get hasActiveFilters() {
			return hasActiveFilters;
		},

		async fetchAll(projectSlug: string, page?: number, force: boolean = false) {
			if (isLoading && !force && projectSlug === filters.projectSlug) return;

			if (!force && hasFetched && projectSlug === filters.projectSlug && page === undefined) {
				return;
			}

			const projectChanged = projectSlug !== filters.projectSlug;
			if (projectChanged) {
				targets = [];
				organizations = [];
				tags = [];
				hasFetched = false;
				summaryLoaded = false;
				countsLoaded = false;
				loadError = null;
				if (filters.projectSlug !== undefined) pagination.currentPage = 1;
			}

			if (page !== undefined) {
				pagination.currentPage = page;
			}

			const my = ++seq;
			isLoading = true;
			error = null;
			filters.projectSlug = projectSlug;

			try {
				const baseFilters = scopeFilters(projectSlug);

				const shouldFetchOrgsAndTags =
					!hasFetched ||
					projectChanged ||
					organizationsSlug !== projectSlug ||
					tagsSlug !== projectSlug;

				// the list decides the page; the strip, tabs and facets may fail on their own
				const extras = Promise.allSettled([
					targetsApi.getStats(baseFilters),
					targetsApi.getCounts(countFilters(projectSlug)),
					shouldFetchOrgsAndTags
						? organizationsApi.list({ project_slug: projectSlug })
						: Promise.resolve(null),
					shouldFetchOrgsAndTags
						? tagsApi.list({ project_slug: projectSlug })
						: Promise.resolve(null)
				]);
				const targetsResponse: PaginatedResponse<Target> = await targetsApi.list({
					...baseFilters,
					signal: filters.signalFilter,
					sort_by: filters.sortKey,
					sort_dir: filters.sortDir,
					page: pagination.currentPage,
					size: pagination.pageSize
				});
				const [stats, countsResult, orgsResult, tagsResult] = await extras;
				if (my !== seq) return;

				targets = targetsResponse.items;
				pagination.totalItems = targetsResponse.total;
				pagination.totalPages = targetsResponse.pages;
				summaryLoaded = stats.status === 'fulfilled';
				if (stats.status === 'fulfilled') signalSummary = stats.value;
				countsLoaded = countsResult.status === 'fulfilled';
				if (countsResult.status === 'fulfilled') counts = countsResult.value;

				if (
					shouldFetchOrgsAndTags &&
					orgsResult.status === 'fulfilled' &&
					tagsResult.status === 'fulfilled' &&
					orgsResult.value &&
					tagsResult.value
				) {
					organizations = orgsResult.value;
					tags = tagsResult.value;
					organizationsSlug = tagsSlug = projectSlug;
				}

				hasFetched = true;
				loadError = null;
			} catch (e) {
				if (my !== seq) return;
				error = e instanceof Error ? e.message : 'Targets not loaded';
				loadError = error;
			} finally {
				if (my === seq) isLoading = false;
			}
		},

		applyQueryState(state: {
			search?: string;
			activeTab?: string;
			selectedOrganizations?: string[];
			selectedTags?: string[];
			signalFilter?: SignalFilter | null;
			sortKey?: SortKey;
			sortDir?: SortDir;
			page?: number;
			pageSize?: number;
		}) {
			if (state.search !== undefined) filters.searchQuery = state.search;
			if (state.activeTab !== undefined) filters.activeTab = state.activeTab;
			if (state.selectedOrganizations) filters.selectedOrganizations = state.selectedOrganizations;
			if (state.selectedTags) filters.selectedTags = state.selectedTags;
			if (state.signalFilter !== undefined) filters.signalFilter = state.signalFilter;
			if (state.sortKey) filters.sortKey = state.sortKey;
			if (state.sortDir) filters.sortDir = state.sortDir;
			if (state.page) pagination.currentPage = state.page;
			if (state.pageSize) pagination.pageSize = state.pageSize;
		},

		toQueryString(): string {
			const sp = new SvelteURLSearchParams();
			if (filters.searchQuery.trim()) sp.set('q', filters.searchQuery.trim());
			if (filters.activeTab !== 'all') sp.set('type', filters.activeTab);
			if (filters.signalFilter) sp.set('signal', filters.signalFilter);
			if (filters.sortKey !== 'updated') sp.set('sort', filters.sortKey);
			if (filters.sortDir !== 'desc') sp.set('dir', filters.sortDir);
			for (const id of filters.selectedOrganizations) sp.append('org', id);
			for (const id of filters.selectedTags) sp.append('tag', id);
			if (pagination.currentPage > 1) sp.set('page', String(pagination.currentPage));
			if (pagination.pageSize !== 20) sp.set('size', String(pagination.pageSize));
			return sp.toString();
		},

		async reload() {
			if (!filters.projectSlug) return;
			pagination.currentPage = 1;
			await this.fetchAll(filters.projectSlug, 1, true);
		},

		async refresh() {
			if (!filters.projectSlug) return;
			await this.fetchAll(filters.projectSlug, pagination.currentPage, true);
		},

		async refreshSummary() {
			if (!filters.projectSlug) return;
			try {
				signalSummary = await targetsApi.getStats(scopeFilters(filters.projectSlug));
				summaryLoaded = true;
			} catch {}
		},

		setSearchQuery(query: string) {
			filters.searchQuery = query;
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

		setSignalFilter(signal: SignalFilter | null) {
			filters.signalFilter = signal;
			this.reload();
		},

		setSort(key: SortKey, dir?: SortDir) {
			if (dir) {
				filters.sortKey = key;
				filters.sortDir = dir;
			} else if (filters.sortKey === key) {
				filters.sortDir = filters.sortDir === 'asc' ? 'desc' : 'asc';
			} else {
				filters.sortKey = key;
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
			seeds?: string[];
		}): Promise<Target | null> {
			error = null;
			try {
				const newTarget = await targetsApi.create(data);
				await this.refresh();
				return newTarget;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Target not created';
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
				error = e instanceof Error ? e.message : 'Target not saved';
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

		async bulkEnrich(ids: string[], kind: EnrichmentKind): Promise<number> {
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
				scansStore.markStale();
				dashboardStore.markStale();
				return true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Target not deleted';
				return false;
			}
		},

		async deleteTargets(ids: string[]): Promise<number> {
			const results = await Promise.allSettled(ids.map((id) => targetsApi.delete(id)));
			const ok = results.filter((r) => r.status === 'fulfilled').length;
			if (ok) {
				await this.refresh();
				scansStore.markStale();
				dashboardStore.markStale();
			}
			return ok;
		},

		async fetchTags(projectSlug = filters.projectSlug) {
			if (!projectSlug) return;
			if (projectSlug !== tagsSlug) {
				tags = [];
				tagsSlug = undefined;
			}
			try {
				tags = await tagsApi.list({ project_slug: projectSlug });
				tagsSlug = projectSlug;
			} catch {}
		},

		async fetchOrganizations(projectSlug = filters.projectSlug) {
			if (!projectSlug) return;
			if (projectSlug !== organizationsSlug) {
				organizations = [];
				organizationsSlug = undefined;
			}
			try {
				organizations = await organizationsApi.list({ project_slug: projectSlug });
				organizationsSlug = projectSlug;
			} catch {}
		},

		async createOrganization(projectSlug: string, name: string): Promise<Organization | null> {
			try {
				const row = await organizationsApi.create({ name, project_slug: projectSlug });
				void this.fetchOrganizations(projectSlug);
				return row;
			} catch {
				return null;
			}
		},

		async createTag(projectSlug: string, name: string, color: string): Promise<Tag | null> {
			try {
				const row = await tagsApi.create({ name, color, project_slug: projectSlug });
				void this.fetchTags(projectSlug);
				return row;
			} catch {
				return null;
			}
		},

		async updateTag(id: string, data: TagUpdate): Promise<void> {
			await tagsApi.update(id, data);
			await this.fetchTags(filters.projectSlug);
			void this.refresh();
		},

		async deleteTag(id: string): Promise<void> {
			await tagsApi.remove(id);
			filters.selectedTags = filters.selectedTags.filter((t) => t !== id);
			await this.fetchTags(filters.projectSlug);
			void this.refresh();
		},

		async updateOrganization(id: string, data: OrganizationUpdate): Promise<void> {
			await organizationsApi.update(id, data);
			await this.fetchOrganizations(filters.projectSlug);
			void this.refresh();
		},

		async deleteOrganization(id: string): Promise<void> {
			await organizationsApi.remove(id);
			filters.selectedOrganizations = filters.selectedOrganizations.filter((o) => o !== id);
			await this.fetchOrganizations(filters.projectSlug);
			void this.refresh();
		},

		clear() {
			seq++;
			if (searchDebounce) clearTimeout(searchDebounce);
			isLoading = false;
			targets = [];
			organizations = [];
			tags = [];
			organizationsSlug = tagsSlug = undefined;
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
				pageSize: 20,
				totalItems: 0,
				totalPages: 0
			};
			signalSummary = { ...EMPTY_TARGET_SUMMARY };
			error = null;
			loadError = null;
			hasFetched = false;
			summaryLoaded = false;
			countsLoaded = false;
		}
	};
}

export const targetsStore = createTargetsStore();
