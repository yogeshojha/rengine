<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth.svelte';
	import { onMount } from 'svelte';
	import { ModeWatcher } from 'mode-watcher';

	let { children } = $props();

	onMount(() => {
		auth.checkAuth();
	});
</script>

<ModeWatcher />
{@render children()}
