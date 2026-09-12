<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { ROUTES } from '$lib/config/routes';
	onMount(() => goto(ROUTES.scans));
</script>
