const SESSION_EXPIRED_EVENT = 'auth:session-expired';

export const API_PREFIX = '/api/v1';

export const REQUEST_TIMEOUT_MS = 120_000;
export const LONG_REQUEST_TIMEOUT_MS = 300_000;

const NO_RESPONSE = 'The API did not respond. Check that the api service is running.';

function isTimeout(e: unknown): boolean {
	return e instanceof DOMException && (e.name === 'TimeoutError' || e.name === 'AbortError');
}

async function timedFetch(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
	try {
		return await fetch(url, { ...init, signal: AbortSignal.timeout(timeoutMs) });
	} catch (e) {
		if (isTimeout(e)) throw new Error(NO_RESPONSE);
		throw e;
	}
}

type RefreshResult = 'ok' | 'expired' | 'error';

function extractErrorMessage(detail: unknown, status: number): string {
	if (typeof detail === 'string' && detail.trim()) return detail;
	if (Array.isArray(detail)) {
		const msgs = detail
			.map((d) => (d && typeof d === 'object' && 'msg' in d ? String(d.msg) : ''))
			.filter(Boolean);
		if (msgs.length) return msgs.join('; ');
	}
	return `Request failed with status ${status}`;
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
					'Content-Type': 'application/json',
					...options.headers
				},
				credentials: 'include'
			},
			timeoutMs
		);

		if (!response.ok) {
			if (response.status === 401 && !isRetry && !this.isAuthEndpoint(endpoint)) {
				const result = await this.tryRefresh();
				if (result === 'ok') {
					return this.request<T>(endpoint, options, true, timeoutMs);
				}
				throw new Error(
					result === 'expired'
						? 'Session expired. Sign in again.'
						: 'Session not refreshed. Sign in again.'
				);
			}

			const errorData = await response.json().catch(() => ({}));
			throw new Error(extractErrorMessage(errorData?.detail, response.status));
		}

		if (response.status === 204) {
			return undefined as T;
		}

		return response.json();
	}

	private isAuthEndpoint(endpoint: string): boolean {
		return endpoint.startsWith('/auth/');
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

	async text(endpoint: string, isRetry = false): Promise<string> {
		const response = await timedFetch(
			`${this.baseUrl}${endpoint}`,
			{ credentials: 'include' },
			REQUEST_TIMEOUT_MS
		);
		if (response.ok) return response.text();

		if (response.status === 401 && !isRetry) {
			const result = await this.tryRefresh();
			if (result === 'ok') return this.text(endpoint, true);
			throw new Error(
				result === 'expired'
					? 'Session expired. Sign in again.'
					: 'Session not refreshed. Sign in again.'
			);
		}

		const errorData = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(errorData?.detail, response.status));
	}

	async bytes(endpoint: string, isRetry = false): Promise<ArrayBuffer> {
		const response = await timedFetch(
			`${this.baseUrl}${endpoint}`,
			{ credentials: 'include' },
			REQUEST_TIMEOUT_MS
		);
		if (response.ok) return response.arrayBuffer();

		if (response.status === 401 && !isRetry) {
			const result = await this.tryRefresh();
			if (result === 'ok') return this.bytes(endpoint, true);
			throw new Error(
				result === 'expired'
					? 'Session expired. Sign in again.'
					: 'Session not refreshed. Sign in again.'
			);
		}

		const errorData = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(errorData?.detail, response.status));
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
