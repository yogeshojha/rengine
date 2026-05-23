const SESSION_EXPIRED_EVENT = 'auth:session-expired';

class ApiClient {
    private baseUrl = '/api/v1';

    /**
     * Shared refresh promise — all concurrent 401s wait on the same refresh attempt
     * rather than each firing their own, preventing token thrashing.
     */
    private refreshPromise: Promise<boolean> | null = null;

    private async request<T>(
        endpoint: string,
        options: RequestInit = {},
        isRetry = false
    ): Promise<T> {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            credentials: 'include',
        });

        if (!response.ok) {
            if (response.status === 401 && !isRetry && !this.isAuthEndpoint(endpoint)) {
                const refreshed = await this.tryRefresh();
                if (refreshed) {
                    return this.request<T>(endpoint, options, true);
                }
                throw new Error('Session expired. Please log in again.');
            }

            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API Error: ${response.status}`);
        }

        if (response.status === 204) {
            return undefined as T;
        }

        return response.json();
    }

    /**
     * Auth endpoints (login, refresh, logout) must never trigger a refresh loop.
     */
    private isAuthEndpoint(endpoint: string): boolean {
        return endpoint.startsWith('/auth/');
    }

    /**
     * Attempt a single token refresh. Concurrent callers share the same promise
     * so only one HTTP request is made regardless of how many requests got 401.
     */
    private async tryRefresh(): Promise<boolean> {
        if (this.refreshPromise) {
            return this.refreshPromise;
        }

        this.refreshPromise = this.performRefresh().finally(() => {
            this.refreshPromise = null;
        });

        return this.refreshPromise;
    }

    private async performRefresh(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/auth/refresh`, {
                method: 'POST',
                credentials: 'include',
            });

            if (response.ok) {
                return true;
            }

            this.emitSessionExpired();
            return false;
        } catch {
            this.emitSessionExpired();
            return false;
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

    post<T>(endpoint: string, data?: unknown): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'POST',
            body: data !== undefined ? JSON.stringify(data) : undefined,
        });
    }

    put<T>(endpoint: string, data: unknown): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    }

    patch<T>(endpoint: string, data: unknown): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    delete<T>(endpoint: string): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'DELETE',
        });
    }
}

export const api = new ApiClient();
export { SESSION_EXPIRED_EVENT };
