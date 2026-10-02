<script lang="ts">
	import Hint from '$lib/components/hint.svelte';
	import QueryHighlight from '$lib/components/scans/results/query-bar/query-highlight.svelte';
	import { QUERY_SCHEMAS } from '$lib/stores/query-schema.svelte';
	import type { SurfaceDimension } from '$lib/config/surface';
	import { dimensionSpec } from '$lib/config/tripwires';
	import { lex } from '$lib/utilities/query-lexer';

	interface Props {
		dimension: string;
		query: string;
		wrap?: boolean;
		hint?: boolean;
		class?: string;
	}

	let { dimension, query, wrap = false, hint = true, class: klass = '' }: Props = $props();

	let store = $derived(QUERY_SCHEMAS[dimension as SurfaceDimension]);
	let spec = $derived(dimensionSpec(dimension));

	$effect(() => {
		void store?.load();
	});

	let tokens = $derived(store ? lex(query, (name) => store.byName.has(name)).tokens : []);
	let shape = $derived(wrap ? 'break-all whitespace-pre-wrap' : 'truncate whitespace-nowrap');
</script>

{#if query.trim()}
	<Hint text={wrap || !hint ? null : query}>
		{#snippet child(props)}
			<code
				{...props}
				class="inline-block max-w-full rounded bg-muted px-1.5 py-0.5 align-middle font-mono text-2xs leading-5 {shape} {klass}"
				>{#if store}<QueryHighlight
						source={query}
						{tokens}
						problems={[]}
					/>{:else}{query}{/if}</code
			>
		{/snippet}
	</Hint>
{:else}
	<span class="text-2xs text-muted-foreground {klass}">Any {spec.noun}</span>
{/if}
