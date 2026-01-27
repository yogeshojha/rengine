<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { onMount } from 'svelte';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from "$lib/components/ui/sonner/index.js";

	let { children } = $props();

	onMount(() => {
		auth.checkAuth();
	});
</script>

<ModeWatcher />
<Toaster position="top-center" richColors/>
{@render children()}
