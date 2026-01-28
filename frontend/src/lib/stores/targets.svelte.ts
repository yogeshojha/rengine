import { targetsApi } from '$lib/api/targets';
import { organizationsApi, type Organization } from '$lib/api/organizations';
import { tagsApi, type Tag } from '$lib/api/tags';
import { TargetType, type Target } from '$lib/types/target';

interface TargetFilters {
	projectSlug?: string;
	searchQuery: string;
	activeTab: string;
	selectedOrganizations: string[];
	selectedTags: string[];
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

	let counts = $derived.by(() => {
		const all = targets.length;
		const domain = targets.filter((t) => t.target_type === TargetType.DOMAIN).length;
		const ip = targets.filter((t) => t.target_type === TargetType.IP).length;
		const ip_range = targets.filter((t) => t.target_type === TargetType.IP_RANGE).length;
		const asn = targets.filter((t) => t.target_type === TargetType.ASN).length;
		const url = targets.filter((t) => t.target_type === TargetType.URL).length;
		return { all, domain, ip, ip_range, asn, url };
	});

	let filteredTargets = $derived.by(() => {
		let result = [...targets];

		if (filters.activeTab !== 'all') {
			result = result.filter((t) => t.target_type === filters.activeTab);
		}

		// Filter by search query
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

		// Filter by selected organizations
		if (filters.selectedOrganizations.length > 0) {
			result = result.filter((t) =>
				t.organizations.some((org) => filters.selectedOrganizations.includes(org.id))
			);
		}

		// Filter by selected tags
		if (filters.selectedTags.length > 0) {
			result = result.filter((t) =>
				t.tags.some((tag) => filters.selectedTags.includes(tag.id))
			);
		}

		return result;
	});

	// Computed: check if any filters are active
	let hasActiveFilters = $derived(
		filters.searchQuery.trim() !== '' ||
		filters.selectedOrganizations.length > 0 ||
		filters.selectedTags.length > 0
	);

	return {
		// Getters
		get targets() { return targets; },
		get filteredTargets() { return filteredTargets; },
		get organizations() { return organizations; },
		get tags() { return tags; },
		get counts() { return counts; },
		get filters() { return filters; },
		get isLoading() { return isLoading; },
		get error() { return error; },
		get hasFetched() { return hasFetched; },
		get hasActiveFilters() { return hasActiveFilters; },

		// Fetch all data for a project
		async fetchAll(projectSlug: string) {
			if (isLoading) return;

			// Check if already fetched for this project aviud infinite loops
			if (hasFetched && projectSlug === filters.projectSlug) {
				return;
			}

			// Clear data if project changed
			if (projectSlug !== filters.projectSlug) {
				targets = [];
				organizations = [];
				tags = [];
				hasFetched = false;
			}

			isLoading = true;
			error = null;
			filters.projectSlug = projectSlug;

			try {
				// Fetch all data in parallel
				const [fetchedTargets, fetchedOrgs, fetchedTags] = await Promise.all([
					targetsApi.list({ project_slug: projectSlug }),
					organizationsApi.list({ project_slug: projectSlug }),
					tagsApi.list({ project_slug: projectSlug })
				]);

				targets = fetchedTargets;
				organizations = fetchedOrgs;
				tags = fetchedTags;
				hasFetched = true;
			} catch (e) {
				error = e instanceof Error ? e.message : 'Failed to fetch data';
			} finally {
				isLoading = false;
			}
		},

		// refresh btn
		async refresh() {
			if (!filters.projectSlug) return;
			hasFetched = false;
			await this.fetchAll(filters.projectSlug);
		},

		// Filter setters
		setSearchQuery(query: string) {
			filters.searchQuery = query;
		},

		setActiveTab(tab: string) {
			filters.activeTab = tab;
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
				targets = [newTarget, ...targets];
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
				targets = targets.filter((t) => t.id !== targetId);
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
			filters = {
				searchQuery: '',
				activeTab: 'all',
				selectedOrganizations: [],
				selectedTags: []
			};
			error = null;
			hasFetched = false;
		}
	};
}

export const targetsStore = createTargetsStore();
