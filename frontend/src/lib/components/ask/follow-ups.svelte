<script lang="ts">
	import { linkScan } from './link-scope';
	import Brain from '@lucide/svelte/icons/brain';
	import CornerDownRight from '@lucide/svelte/icons/corner-down-right';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { blockHref } from './block-columns';
	import { FollowUpSource } from '$lib/config/ask';
	import { surfaceSpec } from '$lib/config/surface';
	import type { FollowUp } from '$lib/types/ask';

	interface Props {
		items: FollowUp[];
		loading?: boolean;
		enter?: boolean;
		disabled?: boolean;
		scopeValues?: string[] | null;
		onAsk: (item: FollowUp) => void;
	}

	let {
		items,
		loading = false,
		enter = false,
		disabled = false,
		scopeValues = null,
		onAsk
	}: Props = $props();

	const scan = linkScan();

	const ROW = 'flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted/50';

	function counted(item: FollowUp): string {
		if (item.count == null) return '';
		const spec = surfaceSpec(item.dimension ?? '');
		const noun = item.count === 1 ? spec?.noun : spec?.nounPlural;
		return `${item.count.toLocaleString()}${item.capped ? '+' : ''} ${noun ?? ''}`.trim();
	}
</script>

{#if loading || items.length}
	<section class={['flex flex-col gap-2', enter && 'ask-rise']} aria-label="Next">
		<span class="text-2xs font-medium tracking-wide text-muted-foreground uppercase">Next</span>
		{#if loading}
			<div class="flex flex-col gap-2 rounded-lg border bg-card p-3">
				<Skeleton class="h-4 w-2/3" />
				<Skeleton class="h-4 w-1/2" />
			</div>
		{:else}
			<ul class="flex flex-col divide-y overflow-hidden rounded-lg border bg-card">
				{#each items as item (item.text)}
					{@const href =
						disabled && item.dimension
							? blockHref(item.dimension, item.query ?? null, scopeValues, scan())
							: null}
					<li>
						{#snippet body()}
							{#if item.source === FollowUpSource.MODEL}
								<Brain class="size-3.5 shrink-0 text-primary" />
							{:else}
								<CornerDownRight class="size-3.5 shrink-0 text-muted-foreground" />
							{/if}
							<span class="min-w-0 flex-1 text-sm leading-5">{item.text}</span>
							<span class="shrink-0 text-xs text-muted-foreground tabular-nums"
								>{counted(item)}</span
							>
						{/snippet}
						{#if href}
							<a {href} class={ROW}>{@render body()}</a>
						{:else}
							<button
								type="button"
								{disabled}
								class="{ROW} disabled:opacity-50"
								onclick={() => onAsk(item)}
							>
								{@render body()}
							</button>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</section>
{/if}
