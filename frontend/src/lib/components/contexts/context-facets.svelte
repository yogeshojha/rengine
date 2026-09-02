<script lang="ts">
	import Check from '@lucide/svelte/icons/check';
	import Minus from '@lucide/svelte/icons/minus';
	import { cn } from '$lib/utils';
	import type { ScanContextCreate, ScanContextRead } from '$lib/types/scan-context';
	import { contextFacets, facetLine } from './context-summary';

	interface Props {
		context: ScanContextRead | ScanContextCreate;
		proxyName?: string | null;
		variant?: 'list' | 'inline';
		class?: string;
	}

	let { context, proxyName = null, variant = 'list', class: className }: Props = $props();

	const facets = $derived(contextFacets(context, proxyName));
</script>

{#if variant === 'inline'}
	<p class={cn('text-xs leading-relaxed text-foreground', className)}>
		{facetLine(context, proxyName)}
	</p>
{:else}
	<ul class={cn('flex flex-col gap-1', className)}>
		{#each facets as facet (facet.key)}
			<li
				class={cn(
					'grid grid-cols-[12px_58px_minmax(0,1fr)] items-baseline gap-x-2 text-xs',
					facet.set ? 'text-foreground' : 'text-muted-foreground/70'
				)}
			>
				{#if facet.set}
					<Check size={12} class="relative top-0.5 shrink-0 text-primary" aria-label="Set" />
				{:else}
					<Minus size={12} class="relative top-0.5 shrink-0 opacity-60" aria-label="Default" />
				{/if}
				<span class="text-[10px] tracking-wider text-muted-foreground uppercase">{facet.label}</span
				>
				<span class="min-w-0 leading-snug break-words">{facet.value}</span>
			</li>
		{/each}
	</ul>
{/if}
