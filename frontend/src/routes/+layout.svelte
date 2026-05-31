<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '$lib/components/ui/sonner/index.js';
	import { SESSION_EXPIRED_EVENT } from '$lib/api/client';

	let { children } = $props();

	onMount(() => {
		auth.checkAuth();

		/**
		 * When the API client fails to refresh a token it emits this event.
		 * We clear all session state here and let the (app) layout's $effect
		 * guard redirect to /login — or we do it directly if that layout is
		 * not mounted (edge case: user somehow on a public route).
		 */
		function handleSessionExpired() {
			auth.clearSession();
			goto('/login');
		}

		window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
		return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
	});
</script>

<ModeWatcher />
<Toaster position="top-center" richColors />
{@render children()}
