<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import Globe from '$lib/components/scans/results/overview/globe.svelte';
	import CountryFlag from '$lib/components/scans/results/country-flag.svelte';
	import { countryName } from '$lib/config/country-geo';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { cn } from '$lib/utils';
	import type { DashboardGeo, DashboardTargetCount } from '$lib/types/dashboard';

	interface Props {
		geography: DashboardGeo[];
		total: number;
		ready: boolean;
		class?: string;
	}

	let { geography, total, ready, class: className }: Props = $props();

	const MAX_CHIPS = 6;
	const MAX_TARGETS = 6;
	const IPS = SURFACE[SurfaceDimension.IPS];

	let hovered = $state<string | null>(null);
	let selected = $state<string | null>(null);

	let ranked = $derived(
		[...geography].sort((a, b) => b.count - a.count || a.code.localeCompare(b.code))
	);
	let dominant = $derived(ranked[0] ?? null);
	let rest = $derived(ranked.slice(1));
	let chips = $derived(rest.slice(0, MAX_CHIPS));
	let more = $derived(rest.length - chips.length);
	let elsewhere = $derived(rest.reduce((n, g) => n + g.count, 0));
	let share = $derived(total > 0 && dominant ? (dominant.count / total) * 100 : 0);
	let shareLabel = $derived(share > 0 && share < 1 ? '<1%' : `${Math.round(share)}%`);
	let entries = $derived(ranked.map((g) => ({ code: g.code, count: g.count })));
	let detail = $derived(selected ? (ranked.find((g) => g.code === selected) ?? null) : null);
	let detailTargets = $derived(detail?.targets.slice(0, MAX_TARGETS) ?? []);
	let detailMore = $derived((detail?.targets.length ?? 0) - detailTargets.length);

	const addresses = (n: number) => `${n.toLocaleString()} ${n === 1 ? IPS.noun : IPS.nounPlural}`;
	const hrefFor = (t: DashboardTargetCount, code: string) =>
		ROUTES.scanTab(t.scan_id, IPS.tab, { [IPS.queryParam]: `country:${code}` });
	function pick(code: string) {
		selected = selected === code ? null : code;
	}
</script>

<div class={cn('flex flex-col items-center justify-center gap-5 p-5', className)}>
	<Globe
		{entries}
		size={240}
		class="w-48 sm:w-52 xl:w-56"
		activeCode={hovered ?? selected}
		onPick={pick}
		onHover={(code) => (hovered = code)}
	/>

	<div class="flex w-full flex-col gap-3">
		{#if detail}
			<div class="flex items-center gap-2.5">
				<CountryFlag code={detail.code} showCode={false} />
				<span class="min-w-0 flex-1 truncate text-sm font-medium">{countryName(detail.code)}</span>
				<span class="text-sm font-medium tabular-nums">{detail.count.toLocaleString()}</span>
				<button
					type="button"
					class="flex size-6 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
					onclick={() => (selected = null)}
					aria-label="Show all countries"
				>
					<X class="size-3.5" />
				</button>
			</div>
			<p class="text-xs text-muted-foreground">
				{addresses(detail.count)} across {detail.targets.length}
				{detail.targets.length === 1 ? 'target' : 'targets'}
			</p>
			<ul class="-mx-2 flex flex-col">
				{#each detailTargets as t (t.target_id)}
					<li>
						<a
							href={hrefFor(t, detail.code)}
							class="group flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/50"
						>
							<span class="min-w-0 flex-1 truncate font-mono text-xs">{t.target_value}</span>
							<span class="text-xs font-medium tabular-nums">{t.count.toLocaleString()}</span>
							<ArrowUpRight
								class="size-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
							/>
						</a>
					</li>
				{/each}
			</ul>
			{#if detailMore > 0}
				<p class="text-xs text-muted-foreground">+{detailMore} more targets</p>
			{/if}
		{:else if dominant}
			<button
				type="button"
				class="group flex w-full items-center gap-2.5 text-left"
				onclick={() => pick(dominant.code)}
				onpointerenter={() => (hovered = dominant.code)}
				onpointerleave={() => (hovered = null)}
			>
				<CountryFlag code={dominant.code} showCode={false} />
				<span class="min-w-0 flex-1 truncate text-sm font-medium group-hover:underline">
					{countryName(dominant.code)}
				</span>
				<span class="text-sm font-medium tabular-nums">{dominant.count.toLocaleString()}</span>
				<span class="w-9 shrink-0 text-right text-xs text-muted-foreground tabular-nums">
					{shareLabel}
				</span>
			</button>

			{#if rest.length}
				<p class="text-xs text-muted-foreground">
					<span class="font-medium text-foreground tabular-nums">{elsewhere.toLocaleString()}</span>
					{elsewhere === 1 ? IPS.noun : IPS.nounPlural} in {rest.length}
					{rest.length === 1 ? 'other country' : 'other countries'}
				</p>
				<div class="flex flex-wrap gap-1.5">
					{#each chips as item (item.code)}
						<button
							type="button"
							class="inline-flex h-6 items-center gap-1.5 rounded-md border px-2 text-xs transition-colors hover:border-primary/40 hover:bg-accent/60 {hovered ===
							item.code
								? 'border-primary/40 bg-accent/60'
								: ''}"
							onclick={() => pick(item.code)}
							onpointerenter={() => (hovered = item.code)}
							onpointerleave={() => (hovered = null)}
							aria-label="{countryName(item.code)}, {addresses(item.count)}"
						>
							<CountryFlag code={item.code} showCode={false} />
							<span>{item.code}</span>
							<span class="text-muted-foreground tabular-nums">{item.count}</span>
						</button>
					{/each}
					{#if more > 0}
						<span
							class="inline-flex h-6 items-center rounded-md border border-dashed px-2 text-xs text-muted-foreground"
						>
							+{more} more
						</span>
					{/if}
				</div>
			{:else}
				<p class="text-xs text-muted-foreground">
					All {addresses(total)} are in a single country.
				</p>
			{/if}
		{:else if !ready}
			<Skeleton class="h-5 w-full" />
			<Skeleton class="h-4 w-2/3" />
		{/if}
	</div>
</div>
