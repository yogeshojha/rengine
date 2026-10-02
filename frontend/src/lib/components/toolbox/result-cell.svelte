<script lang="ts">
	import IdentityMark from './identity-mark.svelte';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { TONE_TINT, isExternalHref, safeHref } from '$lib/config/toolbox';
	import type { Cell } from '$lib/types/toolbox';

	interface Props {
		cell: Cell;
		onLookup?: (value: string, tool: string | null) => void;
		onNavigate?: () => void;
	}

	let { cell, onLookup, onNavigate }: Props = $props();

	const href = $derived(safeHref(cell.href));
	const external = $derived(isExternalHref(href ?? ''));
	const lookup = $derived(cell.lookup);
</script>

<span class="flex items-start gap-1.5">
	{#if cell.identity}
		<span class="flex h-5 shrink-0 items-center">
			<IdentityMark identity={cell.identity} class="size-3.5" />
		</span>
	{/if}
	<span
		class="text-sm leading-5 {TONE_TINT[cell.tone]} {cell.mono
			? 'font-mono text-xs break-all'
			: 'break-words'}"
	>
		{#if href}
			<a
				{href}
				target={external ? '_blank' : undefined}
				rel={external ? 'noreferrer' : undefined}
				onclick={() => !external && onNavigate?.()}
				class="inline-flex items-center gap-1 hover:text-primary"
			>
				{cell.value}
				{#if external}<ArrowUpRight class="size-3 shrink-0" />{/if}
			</a>
		{:else if lookup && onLookup}
			<button
				type="button"
				onclick={() => onLookup(lookup.value, lookup.tool)}
				class="text-left hover:text-primary">{cell.value}</button
			>
		{:else}
			{cell.value}
		{/if}
		{#if cell.note}
			<span class="text-xs text-muted-foreground"> {cell.note}</span>
		{/if}
	</span>
</span>
