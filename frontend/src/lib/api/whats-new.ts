import type {
	NewFeed,
	NewFeedParams,
	NewMark,
	NewUnseen,
	VisualFeed,
	VisualParams
} from '$lib/types/whats-new';
import { viewerZone } from '$lib/utilities/dates';
import { api } from './client';

function query(params: Record<string, unknown>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		search.set(key, String(value));
	}
	return `?${search.toString()}`;
}

export const whatsNewApi = {
	feed(projectId: string, params: NewFeedParams = {}): Promise<NewFeed> {
		return api.get<NewFeed>(
			`/whats-new${query({ project_id: projectId, tz: viewerZone(), ...params })}`
		);
	},
	visual(projectId: string, params: VisualParams = {}): Promise<VisualFeed> {
		return api.get<VisualFeed>(
			`/whats-new/visual${query({ project_id: projectId, tz: viewerZone(), ...params })}`
		);
	},
	unseen(projectId: string): Promise<NewUnseen> {
		return api.get<NewUnseen>(
			`/whats-new/unseen${query({ project_id: projectId, tz: viewerZone() })}`
		);
	},
	caughtUp(projectId: string): Promise<NewMark> {
		return api.post<NewMark>(`/whats-new/seen${query({ project_id: projectId })}`, {});
	}
};
