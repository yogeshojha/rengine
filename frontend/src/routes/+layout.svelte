<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { SESSION_EXPIRED_EVENT } from '$lib/api/client';
	import { ROUTES } from '$lib/config/routes';
	import { markSessionExpired } from '$lib/components/auth/login';

	let { children } = $props();

	onMount(() => {
		auth.checkAuth();

		function handleSessionExpired() {
			auth.clearSession();
			const { pathname, search } = window.location;
			if (pathname === ROUTES.login) return;
			markSessionExpired();
			goto(ROUTES.loginThen(pathname + search));
		}

		window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
		return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
	});
</script>

<ModeWatcher disableHeadScriptInjection />
<Toaster position="top-center" />
<Tooltip.Provider delayDuration={300} ignoreNonKeyboardFocus>
	{@render children()}
</Tooltip.Provider>
