import type {
	BountyEvent,
	BountyImportResult,
	BountySettings,
	BountySettingsUpdate,
	BountyProgram,
	BountyProgramDetail,
	BountyProgramFilters,
	BountyStatus,
	BountyVocabulary
} from '$lib/types/bounty-program';
import { BountyPlatform } from '$lib/types/bounty-program';
import type { PaginatedResponse } from '$lib/types/pagination';
import { api, toQuery } from './client';

export const bountyProgramsApi = {
	async vocabulary(): Promise<BountyVocabulary> {
		return api.get<BountyVocabulary>('/bounty-programs/vocabulary');
	},

	async status(): Promise<BountyStatus> {
		return api.get<BountyStatus>('/bounty-programs/status');
	},

	async list(
		filters: BountyProgramFilters,
		page: number,
		size: number,
		projectId?: string
	): Promise<PaginatedResponse<BountyProgram>> {
		return api.get<PaginatedResponse<BountyProgram>>(
			`/bounty-programs${toQuery({ ...filters, page, size, project_id: projectId })}`
		);
	},

	async detail(
		handle: string,
		projectId?: string,
		platform: string = BountyPlatform.HackerOne
	): Promise<BountyProgramDetail> {
		return api.get<BountyProgramDetail>(
			`/bounty-programs/${platform}/${encodeURIComponent(handle)}${toQuery({
				project_id: projectId
			})}`
		);
	},

	async events(
		page: number,
		size: number,
		kind?: string | null
	): Promise<PaginatedResponse<BountyEvent>> {
		return api.get<PaginatedResponse<BountyEvent>>(
			`/bounty-programs/events${toQuery({ page, size, kind })}`
		);
	},

	async markEventsSeen(): Promise<unknown> {
		return api.post('/bounty-programs/events/seen', {});
	},

	async settings(): Promise<BountySettings> {
		return api.get<BountySettings>('/bounty-programs/settings');
	},

	async saveSettings(patch: BountySettingsUpdate): Promise<BountySettings> {
		return api.put<BountySettings>('/bounty-programs/settings', patch);
	},

	async syncFeed(): Promise<unknown> {
		return api.post('/bounty-programs/sync-feed', {});
	},

	async sync(scopes = true, platform?: string): Promise<unknown> {
		return api.post(`/bounty-programs/sync${toQuery({ platform, scopes })}`, {});
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
