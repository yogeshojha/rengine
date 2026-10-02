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
