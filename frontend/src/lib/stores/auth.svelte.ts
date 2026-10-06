import { toast } from 'svelte-sonner';
import { authApi, type User } from '$lib/api/auth';
import { retryTransient } from '$lib/api/client';
import { watchesStore } from '$lib/stores/watches.svelte';
import { whatsNewStore } from '$lib/stores/whats-new.svelte';
import { projectsStore } from '$lib/stores/projects.svelte';
import { notificationStore } from '$lib/stores/notifications.svelte';
import { capabilitiesStore } from '$lib/stores/capabilities.svelte';
import { onboardingStore } from '$lib/stores/onboarding.svelte';
import { proxiesStore } from '$lib/stores/proxies.svelte';
import { notificationChannelsStore } from '$lib/stores/notificationChannels.svelte';
import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
import { targetsStore } from '$lib/stores/targets.svelte';
import { scansStore } from '$lib/stores/scans.svelte';
import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
import { scanEnginesStore } from '$lib/stores/scan-engines.svelte';
import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
import { QUERY_SCHEMAS } from './query-schema.svelte';
import { dashboardStore } from '$lib/stores/dashboard.svelte';
import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
import { activityFeed } from '$lib/stores/activity-feed.svelte';
import { liveScans } from '$lib/stores/live-scans.svelte';
import { connectors } from '$lib/stores/connectors.svelte';
import { issueTrackers } from '$lib/stores/issue-trackers.svelte';
import { toolbox } from '$lib/stores/toolbox.svelte';
import { rechecks } from './rechecks.svelte';
import { notes } from './notes.svelte';
import { wordlists } from '$lib/stores/wordlists.svelte';
import { exportsStore } from '$lib/stores/exports.svelte';
import { reports } from '$lib/stores/reports.svelte';
import { reportCatalog } from '$lib/stores/report-catalog.svelte';
import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
import { surfaceStore } from '$lib/stores/surface.svelte';
import { recent } from '$lib/stores/recent.svelte';
import { ai } from '$lib/stores/ai.svelte';
import { mcp } from '$lib/stores/mcp.svelte';
import { remoteControl } from '$lib/stores/remote-control.svelte';
import { tripwiresStore } from '$lib/stores/tripwires.svelte';
import { clearServiceLookup } from '$lib/utilities/service-lookup';
import { clearFindings } from '$lib/components/scans/history/findings';
import { forgetPeeks } from '$lib/components/scans/results/vulnerabilities/findings/peek';
import { forgetBriefs } from '$lib/api/ask';

export const NO_SESSION =
	'Session not started. Check that the instance is served over HTTPS and the api service is running.';

const SESSION_RETRY_MS = [1_000, 3_000, 10_000] as const;

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
			state.user = await retryTransient(() => authApi.me(), SESSION_RETRY_MS);
			state.isAuthenticated = true;
		} catch {
			state.user = null;
			state.isAuthenticated = false;
		} finally {
			state.isLoading = false;
		}
	}

	async function refreshUser() {
		try {
			state.user = await authApi.me();
		} catch {}
	}

	async function login(
		username: string,
		password: string
	): Promise<{
		success: boolean;
		mfaRequired?: boolean;
		mfaToken?: string | null;
		error?: string;
	}> {
		try {
			const res = await authApi.login({ username, password });
			if (res.mfa_required) {
				return { success: false, mfaRequired: true, mfaToken: res.mfa_token };
			}
			await checkAuth();
			if (!state.isAuthenticated) return { success: false, error: NO_SESSION };
			toast.success('Logged in');
			return { success: true };
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Not logged in';
			return { success: false, error: message };
		}
	}

	async function logout() {
		try {
			await authApi.logout();
		} catch {}
		clearSession();
	}

	function clearSession() {
		state.user = null;
		state.isAuthenticated = false;
		projectsStore.clear();
		watchesStore.clear();
		whatsNewStore.clear();
		notificationStore.reset();
		capabilitiesStore.reset();
		onboardingStore.clear();
		proxiesStore.clear();
		notificationChannelsStore.clear();
		scanSchedulesStore.clear();
		instanceSettingsStore.clear();
		targetsStore.clear();
		scansStore.clear();
		scanContextsStore.clear();
		scanEnginesStore.clear();
		engineCatalogStore.clear();
		for (const store of Object.values(QUERY_SCHEMAS)) store.reset();
		dashboardStore.clear();
		breadcrumbStore.clear();
		recent.reset();
		activityFeed.reset();
		liveScans.clear();
		rechecks.reset();
		notes.reset();
		wordlists.reset();
		reports.reset();
		exportsStore.reset();
		reportCatalog.reset();
		interestCatalog.reset();
		bountyVocabulary.reset();
		surfaceStore.reset();
		ai.reset();
		mcp.reset();
		remoteControl.reset();
		connectors.reset();
		issueTrackers.reset();
		tripwiresStore.clear();
		toolbox.reset();
		clearServiceLookup();
		clearFindings();
		forgetPeeks();
		forgetBriefs();
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
		refreshUser,
		login,
		logout,
		clearSession
	};
}

export const auth = createAuthStore();
