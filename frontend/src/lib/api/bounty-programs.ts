import type {
	BountyEvent,
	BountyImportResult,
	BountySettings,
	BountySettingsUpdate,
	BountyProgram,
	BountyProgramDetail,
	BountyProgramFilters,
	BountyStatus,
	BountyVocabulary,
	ScopeState
} from '$lib/types/bounty-program';
import { BountyPlatform } from '$lib/types/bounty-program';
import { api } from './client';

export interface Paged<T> {
	items: T[];
	total: number;
	page: number;
	size: number;
	pages: number;
}

export interface ProgramPage {
	items: BountyProgram[];
	total: number;
	page: number;
	size: number;
	pages: number;
}

function query(params: Record<string, unknown>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		search.set(key, String(value));
	}
	const qs = search.toString();
	return qs ? `?${qs}` : '';
}

export const bountyProgramsApi = {
	async vocabulary(): Promise<BountyVocabulary> {
		return api.get<BountyVocabulary>('/bounty-programs/vocabulary');
	},

	async status(platform: string = BountyPlatform.HackerOne): Promise<BountyStatus> {
		return api.get<BountyStatus>(`/bounty-programs/status${query({ platform })}`);
	},

	async list(
		filters: BountyProgramFilters,
		page: number,
		size: number,
		projectId?: string,
		platform: string = BountyPlatform.HackerOne
	): Promise<ProgramPage> {
		return api.get<ProgramPage>(
			`/bounty-programs${query({ ...filters, platform, page, size, project_id: projectId })}`
		);
	},

	async detail(
		handle: string,
		projectId?: string,
		scope?: ScopeState | null,
		platform: string = BountyPlatform.HackerOne
	): Promise<BountyProgramDetail> {
		return api.get<BountyProgramDetail>(
			`/bounty-programs/${platform}/${encodeURIComponent(handle)}${query({
				project_id: projectId,
				scope
			})}`
		);
	},

	async events(
		page: number,
		size: number,
		kind?: string | null,
		handle?: string | null,
		platform: string = BountyPlatform.HackerOne
	): Promise<Paged<BountyEvent>> {
		return api.get<Paged<BountyEvent>>(
			`/bounty-programs/events${query({ platform, page, size, kind, handle })}`
		);
	},

	async markEventsSeen(): Promise<unknown> {
		return api.post('/bounty-programs/events/seen', {});
	},

	async settings(platform: string = BountyPlatform.HackerOne): Promise<BountySettings> {
		return api.get<BountySettings>(`/bounty-programs/settings${query({ platform })}`);
	},

	async saveSettings(
		patch: BountySettingsUpdate,
		platform: string = BountyPlatform.HackerOne
	): Promise<BountySettings> {
		return api.put<BountySettings>(`/bounty-programs/settings${query({ platform })}`, patch);
	},

	async sync(scopes = true, platform: string = BountyPlatform.HackerOne): Promise<unknown> {
		return api.post(`/bounty-programs/sync${query({ platform, scopes })}`, {});
	},

	async syncProgram(handle: string, platform: string = BountyPlatform.HackerOne): Promise<unknown> {
		return api.post(`/bounty-programs/${platform}/${encodeURIComponent(handle)}/sync`, {});
	},

	async importScopes(
		handle: string,
		projectId: string,
		scopeIds?: string[],
		includeOutOfScope = false,
		groupByProgram = true,
		organizationName = '',
		tags: string[] = [],
		platform: string = BountyPlatform.HackerOne
	): Promise<BountyImportResult> {
		return api.post<BountyImportResult>(
			`/bounty-programs/${platform}/${encodeURIComponent(handle)}/import`,
			{
				project_id: projectId,
				scope_ids: scopeIds ?? null,
				include_out_of_scope: includeOutOfScope,
				group_by_program: groupByProgram,
				organization_name: organizationName || null,
				tags
			}
		);
	}
};
