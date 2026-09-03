<script lang="ts">
	import type { QueryExampleSpec } from '$lib/types/asset-query';

	interface Props {
		example: QueryExampleSpec;
		onPick: (query: string) => void;
	}

	let { example, onPick }: Props = $props();
</script>

<button
	type="button"
	class="group flex min-w-0 flex-col gap-1 rounded-lg border border-border/60 bg-background/40 px-3 py-2.5 text-left transition-colors hover:border-primary/40 hover:bg-accent/60"
	onclick={() => onPick(example.query)}
>
	<span class="truncate text-sm text-foreground">{example.description}</span>
	<span class="truncate font-mono text-xs text-primary/80 group-hover:text-primary"
		>{example.query}</span
	>
</button>
