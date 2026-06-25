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

	let { children } = $props();

	onMount(() => {
		auth.checkAuth();

		function handleSessionExpired() {
			auth.clearSession();
			goto(ROUTES.login);
		}

		window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
		return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
	});
</script>

<ModeWatcher />
<Toaster position="top-center" />
<Tooltip.Provider delayDuration={300}>
	{@render children()}
</Tooltip.Provider>
