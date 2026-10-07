<script lang="ts">
	import { untrack } from 'svelte';
	import Cell from './cell.svelte';
	import { useScopedRoutes } from './scope-links';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { BAND_RAIL, EXPOSURE_PARAMS, INTEREST_TAB } from '$lib/config/interest';
	import { INTEREST_BAND, type InterestPage } from '$lib/types/interest';
	import { scopeToParams } from '$lib/utilities/dashboard-scope';

	interface Props {
		page: InterestPage | null;
		scanId?: string | null;
		loading?: boolean;
		class?: string;
	}

	let { page, scanId = null, loading = false, class: className = '' }: Props = $props();

	const routes = useScopedRoutes();
	const scoped = (filter: Record<string, string> = {}) =>
		ROUTES.exposures(undefined, scopeToParams(new URLSearchParams(filter), routes.scope));
	const link = () => (scanId ? ROUTES.scanTab(scanId, INTEREST_TAB) : scoped());
	const rowLink = (filter: Record<string, string>) => (scanId ? undefined : scoped(filter));

	const BANDS = [INTEREST_BAND.CRITICAL, INTEREST_BAND.HIGH, INTEREST_BAND.NOTABLE] as const;
	const TOP = 6;

	$effect(() => {
		untrack(() => interestCatalog.load());
	});

	const OTHER = 'other';
	let bands = $derived.by(() => {
		const counts = page?.summary.bands ?? {};
		const known: string[] = [...BANDS];
		const other = Object.entries(counts)
			.filter(([key]) => !known.includes(key))
			.reduce((n, [, count]) => n + count, 0);
		return [
			...BANDS.map((b) => ({ key: b as string, count: counts[b] ?? 0 })),
			{ key: OTHER, count: other }
		].filter((b) => b.count > 0);
	});
	let kinds = $derived<BarRow[]>(
		Object.entries(page?.summary.kinds ?? {})
			.sort((a, b) => b[1] - a[1])
			.slice(0, TOP)
			.map(([kind, count]) => ({
				key: kind,
				label: interestCatalog.label(kind),
				count,
				href: rowLink({ [EXPOSURE_PARAMS.kind]: kind })
			}))
	);
	let total = $derived(page?.summary.total ?? 0);
</script>

<Cell
	id="exposures"
	description="Web assets flagged, by reason"
	href={link()}
	hrefLabel="{total.toLocaleString()} flagged"
	loading={loading && !page}
	class={className}
>
	{#if bands.length}
		<div class="grid grid-cols-[repeat(auto-fit,minmax(6rem,1fr))] gap-2">
			{#each bands as b (b.key)}
				{@const href = b.key === OTHER ? undefined : rowLink({ [EXPOSURE_PARAMS.band]: b.key })}
				<svelte:element
					this={href ? 'a' : 'div'}
					{href}
					class="flex flex-col gap-0.5 rounded-lg border bg-muted/20 px-2.5 py-2 {href
						? 'transition-colors hover:bg-muted/50'
						: ''}"
				>
					<span class="flex items-center gap-1.5 text-2xs text-muted-foreground">
						<span class="size-1.5 rounded-full {BAND_RAIL[b.key] ?? 'bg-muted-foreground'}"></span>
						{b.key === OTHER ? 'Other' : interestCatalog.bandLabel(b.key)}
					</span>
					<span class="text-lg leading-none font-semibold tracking-tight tabular-nums">
						{b.count.toLocaleString()}
					</span>
				</svelte:element>
			{/each}
		</div>
	{/if}
	{#if kinds.length}
		<RankedBars rows={kinds} />
	{/if}
</Cell>
