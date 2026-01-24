<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$stores/auth.svelte';
	import { Navbar } from '$components/layout';

	let { children } = $props();

	// Redirect to login if not authenticated
	$effect(() => {
		if (!auth.isLoading && !auth.isAuthenticated) {
			goto('/login');
		}
	});
</script>

{#if auth.isLoading}
	<div class="min-h-screen flex items-center justify-center">
		<p class="text-muted-foreground">Loading...</p>
	</div>
{:else if auth.isAuthenticated}
	<div class="min-h-screen flex flex-col">
		<Navbar />
		<main class="flex-1 container py-6">
			{@render children()}
		</main>
	</div>
{/if}
