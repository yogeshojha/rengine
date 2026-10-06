<script lang="ts">
	import QueryHighlight from '$lib/components/scans/results/query-bar/query-highlight.svelte';
	import { lex } from '$lib/utilities/query-lexer';
	import { cn } from '$lib/utils.js';

	interface Props {
		query: string | null;
		class?: string;
	}

	let { query, class: className }: Props = $props();

	const FIELD = /^[a-z][a-z0-9_]*(\.[a-z0-9_-]+)*$/i;
	let lexed = $derived(query ? lex(query, (name) => FIELD.test(name)) : null);
</script>

<code class={cn('font-mono text-xs leading-5 wrap-anywhere', className)}>
	{#if query && lexed}
		<QueryHighlight source={query} tokens={lexed.tokens} problems={[]} />
	{:else}
		<span class="text-muted-foreground">every row</span>
	{/if}
</code>
