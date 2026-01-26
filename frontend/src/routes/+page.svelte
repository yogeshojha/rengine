<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';

	$effect(() => {
		if (!auth.isLoading) {
			if (auth.isAuthenticated) {
				goto('/dashboard');
			} else {
				goto('/login');
			}
		}
	});
</script>

<div class="min-h-screen flex items-center justify-center">
	<p class="text-muted-foreground">Loading...</p>
</div>
