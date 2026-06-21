import { toast } from 'svelte-sonner';
import { authApi, type User } from '$lib/api/auth';
import { projectsStore } from '$lib/stores/projects.svelte';
import { notificationStore } from '$lib/stores/notifications.svelte';
import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
import { onboardingStore } from '$lib/stores/onboarding.svelte';
import { proxiesStore } from '$lib/stores/proxies.svelte';
import { notificationChannelsStore } from '$lib/stores/notificationChannels.svelte';

interface AuthState {
	user: User | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

function createAuthStore() {
	const state = $state<AuthState>({
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
	): Promise<{ success: boolean; mfaRequired?: boolean; mfaToken?: string | null; error?: string }> {
		try {
			const res = await authApi.login({ username, password });
			if (res.mfa_required) {
				return { success: false, mfaRequired: true, mfaToken: res.mfa_token };
			}
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
		}
		clearSession();
	}

	function clearSession() {
		state.user = null;
		state.isAuthenticated = false;
		projectsStore.clear();
		notificationStore.reset();
		capabilitiesStore.reset();
		onboardingStore.clear();
		proxiesStore.clear();
		notificationChannelsStore.clear();
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
