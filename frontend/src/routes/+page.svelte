<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { ROUTES } from '$lib/config/routes';

	$effect(() => {
		if (!auth.isLoading) {
			// unreachable: the app shell shows the server state with a retry, not the login form
			if (auth.isAuthenticated || auth.unreachable) {
				goto(ROUTES.dashboard, { replaceState: true });
			} else {
				goto(ROUTES.login, { replaceState: true });
			}
		}
	});
</script>

<div class="min-h-screen flex flex-col items-center justify-center gap-3">
	<Spinner />
	<p class="text-muted-foreground">Loading…</p>
</div>
