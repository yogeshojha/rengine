<script lang="ts">
	import { untrack } from 'svelte';
	import Cell from './cell.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import { interestCatalog } from '$lib/stores/interest-catalog.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { BAND_RAIL, INTEREST_TAB } from '$lib/config/interest';
	import { INTEREST_BAND, type InterestPage } from '$lib/types/interest';

	interface Props {
		page: InterestPage | null;
		scanId?: string | null;
		loading?: boolean;
		class?: string;
	}

	let { page, scanId = null, loading = false, class: className = '' }: Props = $props();

	const link = (q?: string) =>
		scanId
			? ROUTES.scanTab(scanId, INTEREST_TAB)
			: ROUTES.exposures(undefined, q ? { q } : undefined);
	const rowLink = (q: string) => (scanId ? undefined : link(q));

	const BANDS = [INTEREST_BAND.CRITICAL, INTEREST_BAND.HIGH, INTEREST_BAND.NOTABLE] as const;
	const TOP = 6;

	$effect(() => {
		untrack(() => interestCatalog.load());
	});

	let bands = $derived(
		BANDS.map((b) => ({ key: b, count: page?.summary.bands[b] ?? 0 })).filter((b) => b.count > 0)
	);
	let kinds = $derived<BarRow[]>(
		Object.entries(page?.summary.kinds ?? {})
			.sort((a, b) => b[1] - a[1])
			.slice(0, TOP)
			.map(([kind, count]) => ({
				key: kind,
				label: interestCatalog.kind(kind)?.label ?? kind.replace(/_/g, ' '),
				count,
				href: rowLink(`exposure:${kind}`)
			}))
	);
	let total = $derived(page?.summary.total ?? 0);
</script>

<Cell
	id="exposures"
	title="Exposures"
	description="Web assets flagged, by reason"
	href={link()}
	hrefLabel="{total.toLocaleString()} flagged"
	loading={loading && !page}
	class={className}
>
	{#if bands.length}
		<div class="grid grid-cols-3 gap-2">
			{#each bands as b (b.key)}
				<svelte:element
					this={scanId ? 'div' : 'a'}
					href={rowLink(`exposure_band:${b.key}`)}
					class="flex flex-col gap-0.5 rounded-lg border bg-muted/20 px-2.5 py-2 transition-colors {scanId
						? ''
						: 'hover:bg-muted/50'}"
				>
					<span class="flex items-center gap-1.5 text-2xs text-muted-foreground">
						<span class="size-1.5 rounded-full {BAND_RAIL[b.key]}"></span>
						{interestCatalog.bandLabel(b.key)}
					</span>
					<span class="text-lg leading-none font-semibold tracking-tight tabular-nums">
						{b.count.toLocaleString()}
					</span>
				</svelte:element>
			{/each}
		</div>
	{/if}
	{#if kinds.length}
		<RankedBars rows={kinds} dense />
	{/if}
</Cell>
