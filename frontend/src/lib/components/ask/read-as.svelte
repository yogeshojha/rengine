<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Hint from '$lib/components/hint.svelte';
	import QueryCode from './query-code.svelte';
	import { ReadKind } from '$lib/config/ask';
	import { surfaceSpec } from '$lib/config/surface';
	import { cn } from '$lib/utils.js';
	import type { ReadToken } from '$lib/types/ask';

	interface Props {
		dimension: string | null;
		reading: ReadToken[];
		query: string | null;
		scope?: string | null;
		label?: boolean;
	}

	let { dimension, reading, query, scope = null, label = true }: Props = $props();

	let spec = $derived(surfaceSpec(dimension ?? ''));
	let open = $state(false);

	const CHIP =
		'inline-flex h-6 max-w-full items-center gap-1 rounded-full border bg-muted/50 px-2 text-xs whitespace-nowrap';
</script>

{#snippet chip(t: ReadToken)}
	<span class={CHIP}>
		{#if t.negated}<span class="text-muted-foreground">not</span>{/if}
		{#if t.kind === ReadKind.FIELD}
			<span class="text-muted-foreground">{t.field}</span>
			<span class="truncate">{t.op ?? ''}{t.text}</span>
		{:else if t.kind === ReadKind.TEXT}
			<span class="truncate">“{t.text}”</span>
		{:else}
			<span class="truncate">{t.text}</span>
		{/if}
	</span>
{/snippet}

<div class="flex min-w-0 flex-col gap-1.5">
	<div class="flex min-w-0 flex-wrap items-center gap-1.5">
		{#if label}
			<span class="mr-0.5 text-xs text-muted-foreground">Read as</span>
		{/if}
		{#if spec}
			<span class={CHIP}>
				<spec.icon class="size-3 text-muted-foreground" />
				{spec.label}
			</span>
		{/if}
		{#each reading as t, i (i)}
			{#if t.kind === ReadKind.OR}
				<span class="text-2xs text-muted-foreground">or</span>
			{:else if t.kind === ReadKind.OPEN || t.kind === ReadKind.CLOSE || t.kind === ReadKind.MORE}
				<span class="text-xs text-muted-foreground">{t.negated ? `not ${t.text}` : t.text}</span>
			{:else if t.hint}
				<Hint text={t.hint}>
					{#snippet child(props)}
						<span {...props} class="inline-flex min-w-0">{@render chip(t)}</span>
					{/snippet}
				</Hint>
			{:else}
				{@render chip(t)}
			{/if}
		{/each}
		{#if scope}
			<span class={cn(CHIP, 'min-w-0')}
				><span class="text-muted-foreground">scope</span><span class="min-w-0 truncate"
					>{scope}</span
				></span
			>
		{/if}
		{#if query}
			<button
				type="button"
				class="inline-flex h-6 items-center gap-0.5 rounded-md px-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
				aria-expanded={open}
				onclick={() => (open = !open)}
			>
				Query
				<ChevronDown class={cn('size-3', open && 'rotate-180')} />
			</button>
		{/if}
	</div>
	{#if open && query}
		<div class="rounded-md border bg-muted/30 px-2.5 py-1.5">
			<QueryCode {query} />
		</div>
	{/if}
</div>
