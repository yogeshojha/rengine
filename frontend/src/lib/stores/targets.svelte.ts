import { targetsApi } from '$lib/api/targets';
import { organizationsApi, type Organization } from '$lib/api/organizations';
import { tagsApi, type Tag } from '$lib/api/tags';
import { TargetType, type Target } from '$lib/types/target';
import type { TargetCounts } from '$lib/types/pagination';

interface TargetFilters {
	projectSlug?: string;
	searchQuery: string;
	activeTab: string;
	selectedOrganizations: string[];
	selectedTags: string[];
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
		selectedTags: []
	});

	let pagination = $state<PaginationState>({
		currentPage: 1,
		pageSize: 50,
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

	let filteredTargets = $derived.by(() => {
		let result = [...targets];

		if (filters.searchQuery.trim()) {
			const query = filters.searchQuery.toLowerCase();
			result = result.filter(
				(t) =>
					t.target_value.toLowerCase().includes(query) ||
					t.display_name?.toLowerCase().includes(query) ||
					t.organizations.some((org) => org.name.toLowerCase().includes(query)) ||
					t.tags.some((tag) => tag.name.toLowerCase().includes(query))
			);
		}

		if (filters.selectedOrganizations.length > 0) {
			result = result.filter((t) =>
				t.organizations.some((org) => filters.selectedOrganizations.includes(org.id))
			);
		}

		if (filters.selectedTags.length > 0) {
			result = result.filter((t) =>
				t.tags.some((tag) => filters.selectedTags.includes(tag.id))
			);
		}

		return result;
	});

	let hasActiveFilters = $derived(
		filters.searchQuery.trim() !== '' ||
		filters.selectedOrganizations.length > 0 ||
		filters.selectedTags.length > 0
	);

	return {
		get targets() { return targets; },
		get filteredTargets() { return filteredTargets; },
		get organizations() { return organizations; },
		get tags() { return tags; },
		get counts() { return counts; },
		get filters() { return filters; },
		get pagination() { return pagination; },
		get isLoading() { return isLoading; },
		get error() { return error; },
		get hasFetched() { return hasFetched; },
		get hasActiveFilters() { return hasActiveFilters; },

		async fetchAll(projectSlug: string, page?: number, force: boolean = false) {
			if (isLoading) return;

			if (!force && hasFetched && projectSlug === filters.projectSlug && page === undefined) {
				return;
			}

			if (projectSlug !== filters.projectSlug) {
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
				const targetType = filters.activeTab !== 'all' ? (filters.activeTab as TargetType) : undefined;

				const shouldFetchOrgsAndTags = !hasFetched || projectSlug !== filters.projectSlug;

				const promises: Promise<any>[] = [
					targetsApi.list({
						project_slug: projectSlug,
						target_type: targetType,
						page: pagination.currentPage,
						size: pagination.pageSize === -1 ? undefined : pagination.pageSize
					})
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

				if (shouldFetchOrgsAndTags) {
					organizations = results[1];
					tags = results[2];
					counts = results[3];
				}

				hasFetched = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to fetch data';
			} finally {
				isLoading = false;
			}
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
		},

		async setActiveTab(tab: string) {
			filters.activeTab = tab;
			pagination.currentPage = 1;
			if (filters.projectSlug) {
				await this.fetchAll(filters.projectSlug, 1, true);
			}
		},

		toggleOrganization(orgId: string) {
			const index = filters.selectedOrganizations.indexOf(orgId);
			if (index === -1) {
				filters.selectedOrganizations = [...filters.selectedOrganizations, orgId];
			} else {
				filters.selectedOrganizations = filters.selectedOrganizations.filter((id) => id !== orgId);
			}
		},

		toggleTag(tagId: string) {
			const index = filters.selectedTags.indexOf(tagId);
			if (index === -1) {
				filters.selectedTags = [...filters.selectedTags, tagId];
			} else {
				filters.selectedTags = filters.selectedTags.filter((id) => id !== tagId);
			}
		},

		clearFilters() {
			filters.searchQuery = '';
			filters.selectedOrganizations = [];
			filters.selectedTags = [];
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
				selectedTags: []
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
