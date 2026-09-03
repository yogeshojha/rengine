<script lang="ts">
	import type { QueryStarter } from '$lib/types/asset-query';

	interface Props {
		example: QueryStarter;
		onPick: (query: string) => void;
	}

	let { example, onPick }: Props = $props();

	let count = $derived('count' in example ? example.count : null);
	let capped = $derived('capped' in example ? example.capped : false);
	let empty = $derived(count === 0);
	let label = $derived(count == null ? '' : `${count.toLocaleString()}${capped ? '+' : ''}`);
	let hint = $derived(
		count == null
			? example.description
			: `${example.description}. ${label} ${count === 1 ? 'host matches' : 'hosts match'}.`
	);
</script>

<button
	type="button"
	aria-label={hint}
	class="group flex min-w-0 flex-col gap-1 rounded-lg border border-border/60 bg-background/40 px-3 py-2.5 text-left transition-colors hover:border-primary/40 hover:bg-accent/60"
	onclick={() => onPick(example.query)}
>
	<span class="flex w-full items-baseline gap-2">
		<span
			class="min-w-0 flex-1 truncate text-sm {empty ? 'text-muted-foreground' : 'text-foreground'}"
			>{example.description}</span
		>
		{#if count != null}
			<span
				class="shrink-0 text-xs tabular-nums {empty
					? 'text-muted-foreground/50'
					: 'text-muted-foreground group-hover:text-foreground'}">{label}</span
			>
		{/if}
	</span>
	<span
		class="w-full truncate font-mono text-xs {empty
			? 'text-muted-foreground/60'
			: 'text-primary/80 group-hover:text-primary'}">{example.query}</span
	>
</button>
