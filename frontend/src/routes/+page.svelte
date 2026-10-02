<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import { ROUTES } from '$lib/config/routes';

	$effect(() => {
		if (!auth.isLoading) {
			if (auth.isAuthenticated) {
				goto(ROUTES.dashboard, { replaceState: true });
			} else {
				goto(ROUTES.login, { replaceState: true });
			}
		}
	});
</script>

<div class="min-h-screen flex items-center justify-center">
	<Spinner />
	<p class="text-muted-foreground">Loading…</p>
</div>
