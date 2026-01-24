<script lang="ts">
	import '../app.css';
	import { auth } from '$stores/auth.svelte';
	import { onMount } from 'svelte';

	let { children } = $props();

	onMount(() => {
		auth.checkAuth();
	});
</script>

{@render children()}
