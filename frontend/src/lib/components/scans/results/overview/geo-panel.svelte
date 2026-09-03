<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Globe from './globe.svelte';
	import CountryFlag from '../country-flag.svelte';
	import { countryName } from '$lib/config/country-geo';
	import { cn } from '$lib/utils';
	import type { InsightTally } from '$lib/utilities/scan-insights';

	interface Props {
		geography: InsightTally[];
		total: number;
		live: boolean;
		ready: boolean;
		class?: string;
		onPick: (code: string) => void;
	}

	let { geography, total, live, ready, class: className, onPick }: Props = $props();

	const MAX_CHIPS = 8;

	let hovered = $state<string | null>(null);

	let ranked = $derived(
		[...geography].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
	);
	let dominant = $derived(ranked[0] ?? null);
	let rest = $derived(ranked.slice(1));
	let chips = $derived(rest.slice(0, MAX_CHIPS));
	let more = $derived(rest.length - chips.length);
	let elsewhere = $derived(rest.reduce((n, t) => n + t.count, 0));
	let share = $derived(total > 0 && dominant ? (dominant.count / total) * 100 : 0);
	let shareLabel = $derived(share > 0 && share < 1 ? '<1%' : `${Math.round(share)}%`);
	let entries = $derived(ranked.map((t) => ({ code: t.name, count: t.count })));
</script>

<div class={cn('flex flex-col items-center justify-center gap-5 p-5', className)}>
	<Globe
		{entries}
		size={240}
		class="w-48 sm:w-52 xl:w-56"
		activeCode={hovered}
		onPick={(code) => onPick(code)}
		onHover={(code) => (hovered = code)}
	/>

	<div class="flex w-full flex-col gap-3">
		{#if dominant}
			<button
				type="button"
				class="group flex w-full items-center gap-2.5 text-left"
				onclick={() => onPick(dominant.name)}
				onpointerenter={() => (hovered = dominant.name)}
				onpointerleave={() => (hovered = null)}
			>
				<CountryFlag code={dominant.name} showCode={false} />
				<span class="min-w-0 flex-1 truncate text-sm font-medium group-hover:underline">
					{countryName(dominant.name)}
				</span>
				<span class="text-sm font-medium tabular-nums">{dominant.count.toLocaleString()}</span>
				<span class="w-9 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
					{shareLabel}
				</span>
			</button>

			{#if rest.length}
				<p class="text-xs text-muted-foreground">
					<span class="font-medium text-foreground tabular-nums">{elsewhere.toLocaleString()}</span>
					{elsewhere === 1 ? 'address' : 'addresses'} in {rest.length}
					{rest.length === 1 ? 'other country' : 'other countries'}
				</p>
				<div class="flex flex-wrap gap-1.5">
					{#each chips as item (item.name)}
						<button
							type="button"
							class="inline-flex h-6 items-center gap-1.5 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60 {hovered ===
							item.name
								? 'border-primary/40 bg-accent/60'
								: ''}"
							onclick={() => onPick(item.name)}
							onpointerenter={() => (hovered = item.name)}
							onpointerleave={() => (hovered = null)}
							aria-label="{countryName(item.name)}, {item.count} addresses"
						>
							<CountryFlag code={item.name} showCode={false} />
							<span>{item.name.toUpperCase()}</span>
							<span class="text-muted-foreground tabular-nums">{item.count}</span>
						</button>
					{/each}
					{#if more > 0}
						<button
							type="button"
							class="inline-flex h-6 items-center rounded-md border border-dashed px-2 text-xs text-muted-foreground hover:text-foreground"
							onclick={() => onPick('')}
						>
							+{more} more
						</button>
					{/if}
				</div>
			{:else}
				<p class="text-xs text-muted-foreground">
					All {total.toLocaleString()} addresses are in a single country.
				</p>
			{/if}

			<Button
				variant="link"
				size="sm"
				class="h-auto gap-1 self-start px-0 text-xs"
				onclick={() => onPick('')}
			>
				View all addresses <ChevronRight class="size-3.5" />
			</Button>
		{:else if !ready}
			<Skeleton class="h-5 w-full" />
			<Skeleton class="h-4 w-2/3" />
		{:else}
			<p class="text-center text-xs text-muted-foreground">
				{live ? 'Locations resolve after IP enrichment.' : 'No location data for this scan.'}
			</p>
		{/if}
	</div>
</div>
