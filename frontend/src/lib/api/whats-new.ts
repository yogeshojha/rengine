import type {
	NewFeed,
	NewFeedParams,
	NewMark,
	NewUnseen,
	VisualFeed,
	VisualParams
} from '$lib/types/whats-new';
import { viewerZone } from '$lib/utilities/dates';
import { api, toQuery } from './client';

export const whatsNewApi = {
	feed(projectId: string, params: NewFeedParams = {}): Promise<NewFeed> {
		return api.get<NewFeed>(
			`/whats-new${toQuery({ project_id: projectId, tz: viewerZone(), ...params })}`
		);
	},
	visual(projectId: string, params: VisualParams = {}): Promise<VisualFeed> {
		return api.get<VisualFeed>(
			`/whats-new/visual${toQuery({ project_id: projectId, tz: viewerZone(), ...params })}`
		);
	},
	unseen(projectId: string): Promise<NewUnseen> {
		return api.get<NewUnseen>(
			`/whats-new/unseen${toQuery({ project_id: projectId, tz: viewerZone() })}`
		);
	},
	caughtUp(projectId: string): Promise<NewMark> {
		return api.post<NewMark>(`/whats-new/seen${toQuery({ project_id: projectId })}`, {});
	}
};
