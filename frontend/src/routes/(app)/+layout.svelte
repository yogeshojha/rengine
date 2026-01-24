<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { AppSidebar, AppHeader } from '$lib/components/layout';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';

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
		<div class="flex flex-col items-center gap-2">
			<div class="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent">
			</div>
			<p class="text-muted-foreground">Loading...</p>
		</div>
	</div>
{:else if auth.isAuthenticated}
	<Sidebar.Provider>
		<AppSidebar />
		<Sidebar.Inset>
			<AppHeader />
			<main class="flex-1 p-4 pt-0">
				{@render children()}
			</main>
		</Sidebar.Inset>
	</Sidebar.Provider>
{/if}