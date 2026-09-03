<script lang="ts">
	import type { Snippet } from 'svelte';
	import { techIconUrl } from '$lib/config/tech-icons';

	interface Props {
		name: string;
		class?: string;
		fallback?: Snippet;
	}

	let { name, class: className = 'size-3', fallback }: Props = $props();

	let failed = $state(false);
	$effect(() => {
		void name;
		failed = false;
	});
	let url = $derived(failed ? null : techIconUrl(name));
</script>

{#if url}
	<img
		src={url}
		alt=""
		aria-hidden="true"
		loading="lazy"
		onerror={() => (failed = true)}
		class="shrink-0 object-contain {className}"
	/>
{:else if fallback}
	{@render fallback()}
{/if}
