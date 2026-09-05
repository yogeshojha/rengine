<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Globe from '@lucide/svelte/icons/globe';

	interface Props {
		host: string;
		path: string;
		onSelect: (host: string, path: string) => void;
	}

	let { host, path, onSelect }: Props = $props();

	let segments = $derived(path.split('/').filter(Boolean));
</script>

<nav class="flex flex-wrap items-center gap-1 text-xs" aria-label="Path">
	{#if host}
		<button
			type="button"
			class="flex items-center gap-1 font-mono hover:text-primary hover:underline"
			onclick={() => onSelect(host, '/')}
		>
			<Globe class="size-3" />
			{host}
		</button>
	{:else}
		<span class="text-muted-foreground">All hosts</span>
	{/if}
	{#each segments as segment, i (i)}
		<ChevronRight class="size-3 shrink-0 text-muted-foreground" />
		<button
			type="button"
			class="font-mono hover:text-primary hover:underline"
			onclick={() => onSelect(host, '/' + segments.slice(0, i + 1).join('/') + '/')}
		>
			{segment}
		</button>
	{/each}
</nav>
