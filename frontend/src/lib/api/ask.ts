import { api } from './client';
import { scopeQuery } from '$lib/utilities/surface-scope';
import { SurfaceDimension } from '$lib/config/surface';
import type {
	AskBrief,
	AskQuestion,
	AskStreamFrame,
	AskSubject,
	AskThread,
	AskThreadCreate,
	AskThreadDetail
} from '$lib/types/ask';

export const askApi = {
	brief(subject: AskSubject): Promise<AskBrief> {
		if (subject.dimension === SurfaceDimension.WEB_ASSETS) {
			const query = new URLSearchParams({ scan_id: subject.scanId, name: subject.key });
			return api.get<AskBrief>(`/ask/brief/web-asset?${query}`);
		}
		const scope = scopeQuery({ projectId: subject.projectId, scanId: subject.scanId });
		return api.get<AskBrief>(`/ask/brief/${subject.briefId ?? ''}?${scope}`);
	},

	threads(subject: AskSubject): Promise<AskThread[]> {
		const query = new URLSearchParams({
			target_id: subject.targetId,
			dimension: subject.dimension,
			asset_key: subject.key
		});
		return api.get<AskThread[]>(`/ask/threads?${query}`);
	},

	createThread(projectId: string, body: AskThreadCreate): Promise<AskThread> {
		return api.post<AskThread>(`/ask/threads?project_id=${projectId}`, body);
	},

	thread(threadId: string): Promise<AskThreadDetail> {
		return api.get<AskThreadDetail>(`/ask/threads/${threadId}`);
	},

	deleteThread(threadId: string): Promise<void> {
		return api.delete<void>(`/ask/threads/${threadId}`);
	},

	deleteThreads(subject: AskSubject): Promise<{ deleted: number }> {
		const query = new URLSearchParams({
			target_id: subject.targetId,
			dimension: subject.dimension,
			asset_key: subject.key
		});
		return api.delete<{ deleted: number }>(`/ask/threads?${query}`);
	},

	ask(
		threadId: string,
		body: AskQuestion,
		onFrame: (frame: AskStreamFrame) => void,
		signal?: AbortSignal
	): Promise<void> {
		return api.stream(
			`/ask/threads/${threadId}/messages`,
			body,
			(event, data) => onFrame({ event, data } as AskStreamFrame),
			signal
		);
	}
};
