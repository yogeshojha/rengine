import { toast } from 'svelte-sonner';
import { authApi, type User } from '$lib/api/auth';
import { projectsStore } from '$lib/stores/projects.svelte';
import { notificationStore } from '$lib/stores/notifications.svelte';

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

	async function login(
		username: string,
		password: string
	): Promise<{ success: boolean; error?: string }> {
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
			// Continue clearing local state even if the API call fails
		}
		clearSession();
	}

	/**
	 * Tear down all session state without making an API call.
	 * Used by both explicit logout and forced expiry (via session-expired event).
	 * Navigation to /login is handled by the (app) layout's $effect guard.
	 */
	function clearSession() {
		state.user = null;
		state.isAuthenticated = false;
		projectsStore.clear();
		notificationStore.reset();
	}

	async function register(
		email: string,
		username: string,
		password: string
	): Promise<{ success: boolean; error?: string }> {
		try {
			await authApi.register({ email, username, password });
			return { success: true };
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Registration failed';
			return { success: false, error: message };
		}
	}

	return {
		get user() {
			return state.user;
		},
		get isAuthenticated() {
			return state.isAuthenticated;
		},
		get isLoading() {
			return state.isLoading;
		},
		checkAuth,
		login,
		logout,
		clearSession,
		register
	};
}

export const auth = createAuthStore();
