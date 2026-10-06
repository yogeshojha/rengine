import { api } from './client';
import { appendTargetScope, scopeQuery, type TargetScope } from '$lib/utilities/surface-scope';
import { SurfaceDimension } from '$lib/config/surface';
import type {
	EstateScanOption,
	AskBrief,
	AskQuestion,
	BlockData,
	EstateQuestion,
	EstateScope,
	EstateStarters,
	EstateStatus,
	EstateStreamFrame,
	EstateThread,
	EstateThreadDetail,
	AskStreamFrame,
	AskSubject,
	AskThread,
	AskThreadCreate,
	AskThreadDetail
} from '$lib/types/ask';

export const BRIEF_TTL_MS = 60_000;
export const BRIEF_LIMIT = 100;

interface HeldBrief {
	at: number;
	promise: Promise<AskBrief>;
	value: AskBrief | null;
}

export function briefKey(subject: AskSubject): string {
	return [
		subject.dimension,
		subject.key,
		subject.scanId,
		subject.briefId ?? '',
		subject.state ?? '',
		subject.reason ?? ''
	].join('\n');
}

export function createBriefCache(
	load: (subject: AskSubject) => Promise<AskBrief>,
	now: () => number = Date.now
) {
	const held = new Map<string, HeldBrief>();
	let lastAvailable: boolean | null = null;

	const fresh = (entry: HeldBrief | undefined): entry is HeldBrief =>
		!!entry && now() - entry.at < BRIEF_TTL_MS;

	return {
		get(subject: AskSubject): Promise<AskBrief> {
			const key = briefKey(subject);
			const hit = held.get(key);
			if (fresh(hit)) return hit.promise;
			held.delete(key);
			if (held.size >= BRIEF_LIMIT) {
				const oldest = held.keys().next();
				if (!oldest.done) held.delete(oldest.value);
			}
			const entry: HeldBrief = { at: now(), promise: load(subject), value: null };
			const forget = () => {
				if (held.get(key) === entry) held.delete(key);
			};
			held.set(key, entry);
			entry.promise.then((brief) => {
				lastAvailable = brief.available;
				if (brief.available) entry.value = brief;
				else forget();
			}, forget);
			return entry.promise;
		},

		peek(subject: AskSubject): AskBrief | null {
			const hit = held.get(briefKey(subject));
			return fresh(hit) ? hit.value : null;
		},

		get lastAvailable(): boolean | null {
			return lastAvailable;
		},

		clear(): void {
			held.clear();
			lastAvailable = null;
		}
	};
}

function fetchBrief(subject: AskSubject): Promise<AskBrief> {
	if (subject.dimension === SurfaceDimension.WEB_ASSETS) {
		const query = new URLSearchParams({ scan_id: subject.scanId, name: subject.key });
		return api.get<AskBrief>(`/ask/brief/web-asset?${query}`);
	}
	const scope = scopeQuery({ projectId: subject.projectId, scanId: subject.scanId });
	return api.get<AskBrief>(`/ask/brief/${subject.briefId ?? ''}?${scope}`);
}

export const askBriefs = createBriefCache(fetchBrief);

export function forgetBriefs(): void {
	askBriefs.clear();
}

export const askApi = {
	brief(subject: AskSubject): Promise<AskBrief> {
		return askBriefs.get(subject);
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

export const estateApi = {
	status(): Promise<EstateStatus> {
		return api.get<EstateStatus>('/ask/estate/status');
	},

	starters(
		projectId: string,
		scope: TargetScope = {},
		scanId: string | null = null
	): Promise<EstateStarters> {
		const query = appendTargetScope(new URLSearchParams({ project_id: projectId }), scope);
		if (scanId) query.set('scan_id', scanId);
		return api.get<EstateStarters>(`/ask/estate/starters?${query}`);
	},

	scans(projectId: string, scope: TargetScope = {}, search = ''): Promise<EstateScanOption[]> {
		const query = appendTargetScope(new URLSearchParams({ project_id: projectId }), scope);
		if (search.trim()) query.set('search', search.trim());
		return api.get<EstateScanOption[]>(`/ask/estate/scans?${query}`);
	},

	threads(projectId: string): Promise<EstateThread[]> {
		return api.get<EstateThread[]>(`/ask/estate/threads?project_id=${projectId}`);
	},

	create(projectId: string, scope: EstateScope): Promise<EstateThread> {
		return api.post<EstateThread>(`/ask/estate/threads?project_id=${projectId}`, { scope });
	},

	thread(threadId: string): Promise<EstateThreadDetail> {
		return api.get<EstateThreadDetail>(`/ask/estate/threads/${threadId}`);
	},

	blocks(threadId: string): Promise<BlockData[]> {
		return api.get<BlockData[]>(`/ask/estate/threads/${threadId}/blocks`);
	},

	page(threadId: string, blockId: string, offset: number): Promise<BlockData> {
		return api.get<BlockData>(`/ask/estate/threads/${threadId}/blocks/${blockId}?offset=${offset}`);
	},

	editQuery(threadId: string, blockId: string, query: string): Promise<BlockData> {
		return api.put<BlockData>(`/ask/estate/threads/${threadId}/blocks/${blockId}/query`, {
			query
		});
	},

	remove(threadId: string): Promise<void> {
		return api.delete<void>(`/ask/estate/threads/${threadId}`);
	},

	ask(
		threadId: string,
		body: EstateQuestion,
		onFrame: (frame: EstateStreamFrame) => void,
		signal?: AbortSignal
	): Promise<void> {
		return api.stream(
			`/ask/estate/threads/${threadId}/messages`,
			body,
			(event, data) => onFrame({ event, data } as EstateStreamFrame),
			signal
		);
	}
};
