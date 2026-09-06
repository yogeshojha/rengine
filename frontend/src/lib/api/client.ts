const SESSION_EXPIRED_EVENT = 'auth:session-expired';

export const API_PREFIX = '/api/v1';

type RefreshResult = 'ok' | 'expired' | 'error';

function extractErrorMessage(detail: unknown, status: number): string {
	if (typeof detail === 'string' && detail.trim()) return detail;
	if (Array.isArray(detail)) {
		const msgs = detail
			.map((d) => (d && typeof d === 'object' && 'msg' in d ? String(d.msg) : ''))
			.filter(Boolean);
		if (msgs.length) return msgs.join('; ');
	}
	return `Request failed (${status})`;
}

class ApiClient {
	private baseUrl = API_PREFIX;

	private refreshPromise: Promise<RefreshResult> | null = null;

	private async request<T>(
		endpoint: string,
		options: RequestInit = {},
		isRetry = false
	): Promise<T> {
		const response = await fetch(`${this.baseUrl}${endpoint}`, {
			...options,
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			credentials: 'include'
		});

		if (!response.ok) {
			if (response.status === 401 && !isRetry && !this.isAuthEndpoint(endpoint)) {
				const result = await this.tryRefresh();
				if (result === 'ok') {
					return this.request<T>(endpoint, options, true);
				}
				throw new Error(
					result === 'expired'
						? 'Session expired. Sign in again.'
						: 'Session could not be refreshed. Sign in again.'
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
			const response = await fetch(`${this.baseUrl}/auth/refresh`, {
				method: 'POST',
				credentials: 'include'
			});

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

	get<T>(endpoint: string): Promise<T> {
		return this.request<T>(endpoint);
	}

	async bytes(endpoint: string, isRetry = false): Promise<ArrayBuffer> {
		const response = await fetch(`${this.baseUrl}${endpoint}`, { credentials: 'include' });
		if (response.ok) return response.arrayBuffer();

		if (response.status === 401 && !isRetry) {
			const result = await this.tryRefresh();
			if (result === 'ok') return this.bytes(endpoint, true);
			throw new Error(
				result === 'expired'
					? 'Session expired. Sign in again.'
					: 'Session could not be refreshed. Sign in again.'
			);
		}

		const errorData = await response.json().catch(() => ({}));
		throw new Error(extractErrorMessage(errorData?.detail, response.status));
	}

	post<T>(endpoint: string, data?: unknown): Promise<T> {
		return this.request<T>(endpoint, {
			method: 'POST',
			body: data !== undefined ? JSON.stringify(data) : undefined
		});
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
