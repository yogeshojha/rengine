import { goto } from '$app/navigation';
import { toast } from 'svelte-sonner';
import { authApi, type User } from '$lib/api/auth';

interface AuthState {
	user: User | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

function createAuthStore() {
	let state = $state<AuthState>({
		user: null,
		isAuthenticated: false,
		isLoading: true
	});

	async function checkAuth() {
		state.isLoading = true;
		try {
			state.user = await authApi.me();
			state.isAuthenticated = true;
		} catch {
			state.user = null;
			state.isAuthenticated = false;
		} finally {
			state.isLoading = false;
		}
	}

	async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
		try {
			await authApi.login({ username, password });
			await checkAuth();
			toast.success('Welcome back, ' + state.user?.username + '!');
			return { success: true };
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Login failed';
			return { success: false, error: message };
		}
	}

	async function logout() {
		try {
			await authApi.logout();
		} catch {
			// Continue with logout even if API call fails
		}
		state.user = null;
		state.isAuthenticated = false;
		goto('/login');
	}

	async function register(email: string, username: string, password: string): Promise<{ success: boolean; error?: string }> {
		try {
			const response = await fetch('/api/v1/auth/register', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ email, username, password })
			});

			if (response.ok) {
				return { success: true };
			} else {
				const data = await response.json();
				return { success: false, error: data.detail || 'Registration failed' };
			}
		} catch {
			return { success: false, error: 'Network error' };
		}
	}

	return {
		get user() { return state.user; },
		get isAuthenticated() { return state.isAuthenticated; },
		get isLoading() { return state.isLoading; },
		checkAuth,
		login,
		logout,
		register
	};
}

export const auth = createAuthStore();
