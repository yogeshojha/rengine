const SESSION_EXPIRED_EVENT = 'auth:session-expired';

export const API_PREFIX = '/api/v1';

export const REQUEST_TIMEOUT_MS = 120_000;
export const LONG_REQUEST_TIMEOUT_MS = 300_000;

export const NO_RESPONSE = 'The API did not respond. Check that the api service is running.';

function isTimeout(e: unknown): boolean {
	return e instanceof DOMException && (e.name === 'TimeoutError' || e.name === 'AbortError');
}

/** A network failure, as distinct from a rejection the caller raised. */
async function unreached<T>(run: () => Promise<T>): Promise<T> {
	try {
		return await run();
	} catch (e) {
		if (e instanceof TypeError) throw new Error(NO_RESPONSE);
		throw e;
	}
}

async function timedFetch(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
	try {
		return await unreached(() => fetch(url, { ...init, signal: AbortSignal.timeout(timeoutMs) }));
	} catch (e) {
		if (isTimeout(e)) throw new Error(NO_RESPONSE);
		throw e;
	}
}

export type RefreshResult = 'ok' | 'expired' | 'error';

const NO_REFRESH = [
	'/auth/login',
	'/auth/2fa/login',
	'/auth/refresh',
	'/auth/logout',
	'/auth/change-password'
];

function refreshes(endpoint: string): boolean {
	return !NO_REFRESH.includes(endpoint.split('?')[0]);
}

export function toQuery(params: Record<string, unknown>): string {
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value === undefined || value === null || value === '') continue;
		if (Array.isArray(value)) for (const item of value) search.append(key, String(item));
		else search.set(key, String(value));
	}
	const qs = search.toString();
	return qs ? `?${qs}` : '';
}

export class ApiError extends Error {
	constructor(
		message: string,
		readonly status: number
	) {
		super(message);
	}
}

/** A failure a retry can clear: no answer, the rate limit or a server error. */
export function isTransient(e: unknown): boolean {
	if (!(e instanceof ApiError)) return true;
	return e.status === 0 || e.status === 429 || e.status >= 500;
}

export async function retryTransient<T>(
	run: () => Promise<T>,
	delays: readonly number[],
	wait: (ms: number) => Promise<void> = (ms) => new Promise((done) => setTimeout(done, ms))
): Promise<T> {
	for (let attempt = 0; ; attempt++) {
		try {
			return await run();
		} catch (e) {
			if (attempt >= delays.length || !isTransient(e)) throw e;
			await wait(delays[attempt]);
		}
	}
}

function sessionError(result: RefreshResult): ApiError {
	return result === 'expired'
		? new ApiError('Session expired. Log in again.', 401)
		: new ApiError('Session not refreshed. Log in again.', 0);
}

async function responseError(response: Response): Promise<ApiError> {
	const errorData = await response.json().catch(() => ({}));
	return new ApiError(extractErrorMessage(errorData?.detail, response.status), response.status);
}

function extractErrorMessage(detail: unknown, status: number): string {
	if (typeof detail === 'string' && detail.trim()) return detail;
	if (Array.isArray(detail)) {
		const msgs = detail
			.map((d) =>
				d && typeof d === 'object' && 'msg' in d ? String(d.msg).replace(/^Value error, /, '') : ''
			)
			.filter(Boolean);
		if (msgs.length) return msgs.join('; ');
	}
	return `Request failed with status ${status}`;
}

function emitFrame(raw: string, onFrame: (event: string, data: unknown) => void): void {
	let event = 'message';
	const lines: string[] = [];
	for (const line of raw.split('\n')) {
		if (line.startsWith('event:')) event = line.slice(6).trim();
		else if (line.startsWith('data:')) lines.push(line.slice(5).trimStart());
	}
	if (!lines.length) return;
	const text = lines.join('\n');
	let data: unknown = text;
	try {
		data = JSON.parse(text);
	} catch {
		/* plain text frame */
	}
	onFrame(event, data);
}

class ApiClient {
	private baseUrl = API_PREFIX;

	private refreshPromise: Promise<RefreshResult> | null = null;

	private inflight = new Map<string, Promise<unknown>>();

	private async request<T>(
		endpoint: string,
		options: RequestInit = {},
		isRetry = false,
		timeoutMs = REQUEST_TIMEOUT_MS
	): Promise<T> {
		const response = await timedFetch(
			`${this.baseUrl}${endpoint}`,
			{
				...options,
				headers: {
					...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
					...options.headers
				},
				credentials: 'include'
			},
			timeoutMs
		);

		if (!response.ok) {
			if (response.status === 401 && !isRetry && refreshes(endpoint)) {
				const result = await this.tryRefresh();
				if (result === 'ok') {
					return this.request<T>(endpoint, options, true, timeoutMs);
				}
				throw sessionError(result);
			}

			throw await responseError(response);
		}

		if (response.status === 204) {
			return undefined as T;
		}

		return response.json();
	}

	refreshSession(): Promise<RefreshResult> {
		return this.tryRefresh();
	}

	private async tryRefresh(): Promise<RefreshResult> {
		if (this.refreshPromise) {
			return this.refreshPromise;
		}

		this.refreshPromise = this.performRefresh().finally(() => {
			this.refreshPromise = null;
		});

		return this.refreshPromise;
	}

	private async performRefresh(): Promise<RefreshResult> {
		try {
			const response = await timedFetch(
				`${this.baseUrl}/auth/refresh`,
				{ method: 'POST', credentials: 'include' },
				REQUEST_TIMEOUT_MS
			);

			if (response.ok) {
				return 'ok';
			}

			if (response.status !== 401 && response.status !== 403) {
				return 'error';
			}

			this.emitSessionExpired();
			return 'expired';
		} catch {
			return 'error';
		}
	}

	private emitSessionExpired(): void {
		if (typeof window !== 'undefined') {
			window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
		}
	}

	get<T>(endpoint: string, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
		const open = this.inflight.get(endpoint);
		if (open) return open as Promise<T>;
		const pending = this.request<T>(endpoint, {}, false, timeoutMs).finally(() => {
			this.inflight.delete(endpoint);
		});
		this.inflight.set(endpoint, pending);
		return pending;
	}

	/** A streamed POST: each SSE frame reaches `onFrame` as it arrives. */
	async stream(
		endpoint: string,
		data: unknown,
		onFrame: (event: string, data: unknown) => void,
		signal?: AbortSignal,
		isRetry = false
	): Promise<void> {
		const body = JSON.stringify(data);
		const response = await unreached(() =>
			fetch(`${this.baseUrl}${endpoint}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body,
				signal
			})
		);
		if (!response.ok) {
			if (response.status === 401 && !isRetry && refreshes(endpoint)) {
				const result = await this.tryRefresh();
				if (result === 'ok') return this.stream(endpoint, data, onFrame, signal, true);
				throw sessionError(result);
			}
			throw await responseError(response);
		}
		if (!response.body) throw new Error(NO_RESPONSE);
		const reader = response.body.getReader();
		const decoder = new TextDecoder();
		let buffer = '';
		for (;;) {
			const { value, done } = await unreached(() => reader.read());
			if (done) break;
			buffer += decoder.decode(value, { stream: true });
			let cut = buffer.indexOf('\n\n');
			while (cut >= 0) {
				emitFrame(buffer.slice(0, cut), onFrame);
				buffer = buffer.slice(cut + 2);
				cut = buffer.indexOf('\n\n');
			}
		}
	}

	/** The response itself, refreshed once on a 401, for bodies that are not JSON. */
	private async raw(endpoint: string, isRetry = false): Promise<Response> {
		const response = await timedFetch(
			`${this.baseUrl}${endpoint}`,
			{ credentials: 'include' },
			REQUEST_TIMEOUT_MS
		);
		if (response.ok) return response;

		if (response.status === 401 && !isRetry && refreshes(endpoint)) {
			const result = await this.tryRefresh();
			if (result === 'ok') return this.raw(endpoint, true);
			throw sessionError(result);
		}

		throw await responseError(response);
	}

	async text(endpoint: string): Promise<string> {
		return (await this.raw(endpoint)).text();
	}

	async bytes(endpoint: string): Promise<ArrayBuffer> {
		return (await this.raw(endpoint)).arrayBuffer();
	}

	post<T>(endpoint: string, data?: unknown, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
		return this.request<T>(
			endpoint,
			{
				method: 'POST',
				body: data !== undefined ? JSON.stringify(data) : undefined
			},
			false,
			timeoutMs
		);
	}

	upload<T>(endpoint: string, body: FormData): Promise<T> {
		return this.request<T>(endpoint, { method: 'POST', body });
	}

	put<T>(endpoint: string, data: unknown): Promise<T> {
		return this.request<T>(endpoint, {
			method: 'PUT',
			body: JSON.stringify(data)
		});
	}

	patch<T>(endpoint: string, data: unknown): Promise<T> {
		return this.request<T>(endpoint, {
			method: 'PATCH',
			body: JSON.stringify(data)
		});
	}

	delete<T>(endpoint: string): Promise<T> {
		return this.request<T>(endpoint, {
			method: 'DELETE'
		});
	}
}

export const api = new ApiClient();
export { SESSION_EXPIRED_EVENT };
