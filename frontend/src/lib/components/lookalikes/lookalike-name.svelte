<script lang="ts">
	import { diffSegments } from '$lib/config/lookalikes';

	interface Props {
		display: string;
		domain: string;
		apex: string;
		class?: string;
	}

	let { display, domain, apex, class: className = '' }: Props = $props();

	let segments = $derived(diffSegments(display, apex));
</script>

<span class="font-mono break-all {className}">
	{#each segments as s, i (i)}
		{#if s.changed}
			<mark class="rounded-[3px] bg-sev-high-wash px-px text-sev-high-ink">{s.text}</mark>
		{:else}
			<span>{s.text}</span>
		{/if}
	{/each}
	{#if display !== domain}
		<span class="ml-1.5 text-2xs text-muted-foreground">{domain}</span>
	{/if}
</span>
