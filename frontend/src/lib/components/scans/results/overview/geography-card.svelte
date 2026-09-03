<script lang="ts">
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import * as Card from '$lib/components/ui/card';
	import CountryFlag from '../country-flag.svelte';
	import SurfaceGlobe from './surface-globe.svelte';
	import { countryName } from '$lib/config/country-geo';
	import type { InsightTally } from '$lib/utilities/scan-insights';

	interface Props {
		geography: InsightTally[];
		total: number;
		onPick: (code: string) => void;
	}

	let { geography, total, onPick }: Props = $props();

	let hovered = $state<string | null>(null);

	let ranked = $derived(
		[...geography].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
	);
	let dominant = $derived(ranked[0] ?? null);
	let rest = $derived(ranked.slice(1));
	let elsewhere = $derived(rest.reduce((n, t) => n + t.count, 0));
	let share = $derived(total > 0 && dominant ? (dominant.count / total) * 100 : 0);
	let shareLabel = $derived(share > 0 && share < 1 ? '<1%' : `${Math.round(share)}%`);
	let entries = $derived(ranked.map((t) => ({ code: t.name, count: t.count })));
</script>

<Card.Root class="overflow-hidden">
	<Card.Header class="gap-1 pb-0">
		<Card.Title class="text-base">Geographic distribution</Card.Title>
		<Card.Description>IP addresses by registered country</Card.Description>
	</Card.Header>
	<Card.Content class="pt-4">
		<div class="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-8">
			<div class="shrink-0">
				<SurfaceGlobe
					{entries}
					size={220}
					activeCode={hovered}
					onPick={(code) => onPick(code)}
					onHover={(code) => (hovered = code)}
				/>
			</div>

			<div class="flex min-w-0 flex-1 flex-col gap-4">
				{#if dominant}
					<button
						type="button"
						class="group flex items-baseline gap-3 text-left"
						onclick={() => onPick(dominant.name)}
						onpointerenter={() => (hovered = dominant.name)}
						onpointerleave={() => (hovered = null)}
					>
						<span class="text-3xl font-semibold tracking-tight tabular-nums">
							{dominant.count.toLocaleString()}
						</span>
						<span class="flex min-w-0 items-baseline gap-2">
							<CountryFlag code={dominant.name} showCode={false} />
							<span class="truncate text-sm group-hover:underline">
								{countryName(dominant.name)}
							</span>
							<span class="shrink-0 text-sm text-muted-foreground tabular-nums">{shareLabel}</span>
						</span>
					</button>
				{/if}

				{#if rest.length}
					<div class="flex flex-col gap-2.5 border-t pt-4">
						<p class="text-sm text-muted-foreground">
							<span class="font-medium text-foreground tabular-nums">
								{elsewhere.toLocaleString()}
							</span>
							{elsewhere === 1 ? 'address' : 'addresses'} in {rest.length}
							{rest.length === 1 ? 'other country' : 'other countries'}
						</p>
						<div class="flex flex-wrap gap-1.5">
							{#each rest as item (item.name)}
								<button
									type="button"
									class="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60 {hovered ===
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
						</div>
					</div>
				{:else}
					<p class="border-t pt-4 text-sm text-muted-foreground">
						All addresses are registered in a single country.
					</p>
				{/if}

				<button
					type="button"
					class="flex items-center gap-1 self-start text-xs text-muted-foreground hover:text-foreground"
					onclick={() => onPick('')}
				>
					View all addresses <ArrowUpRight class="size-3.5" />
				</button>
			</div>
		</div>
	</Card.Content>
</Card.Root>
