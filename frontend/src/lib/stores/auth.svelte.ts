import { goto } from '$app/navigation';
import { toast } from 'svelte-sonner';

export interface User {
	id: string;
	email: string;
	username: string;
	is_active: boolean;
	is_superuser: boolean;
	created_at: string;
}

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
			const response = await fetch('/api/v1/auth/me', {
				credentials: 'include'
			});
			if (response.ok) {
				state.user = await response.json();
				state.isAuthenticated = true;
			} else {
				state.user = null;
				state.isAuthenticated = false;
			}
		} catch {
			state.user = null;
			state.isAuthenticated = false;
		} finally {
			state.isLoading = false;
		}
	}

	async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
		try {
			const response = await fetch('/api/v1/auth/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ username, password })
			});

			if (response.ok) {
				await checkAuth();
				toast.success('Welcome back, ' + state.user?.username + '!');
				return { success: true };
			} else {
				const data = await response.json();
				return { success: false, error: data.detail || 'Login failed' };
			}
		} catch {
			return { success: false, error: 'Network error' };
		}
	}

	async function logout() {
		await fetch('/api/v1/auth/logout', {
			method: 'POST',
			credentials: 'include'
		});
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
