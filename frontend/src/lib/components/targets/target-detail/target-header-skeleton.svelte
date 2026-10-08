<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CellSkeleton from '$lib/components/skeleton/cell-skeleton.svelte';
	import type { SkeletonShape } from '$lib/components/skeleton/shapes';
	import TableSkeleton from '$lib/components/skeleton/table-skeleton.svelte';
	import { ASSET_COLUMNS, ASSET_LEAD_COLUMNS } from './web-assets/columns';
	import { fitColumns } from '$lib/components/scans/results/table/columns';

	interface Props {
		/** The tab the page opens on, so the placeholder has that tab's shape. */
		tab?: string;
	}

	let { tab = 'overview' }: Props = $props();

	let tableWidth = $state(0);
	let assetColumns = $derived(fitColumns(ASSET_COLUMNS, tableWidth, ASSET_LEAD_COLUMNS, false));
</script>

{#snippet cell(shape: SkeletonShape, width: string, rows = 5)}
	<section class="-mr-px -mb-px flex min-w-0 flex-col border-r border-b bg-card {width}">
		<div class="flex items-start justify-between gap-3 px-4 pt-3.5">
			<Skeleton class="h-5 w-28" />
			<Skeleton class="h-3.5 w-12" />
		</div>
		<div class="flex min-h-0 flex-1 flex-col px-4 pt-3 pb-4">
			<CellSkeleton {shape} {rows} />
		</div>
	</section>
{/snippet}

<div class="flex flex-col gap-5" aria-busy="true">
	<div class="flex items-start justify-between gap-4">
		<div class="flex min-w-0 items-start gap-3">
			<Skeleton class="size-10 shrink-0 rounded-lg" />
			<div class="flex min-w-0 flex-col gap-2">
				<Skeleton class="h-6 w-56 max-w-full" />
				<Skeleton class="h-4 w-80 max-w-full" />
			</div>
		</div>
		<div class="flex gap-2">
			<Skeleton class="h-8 w-20" />
			<Skeleton class="size-8" />
		</div>
	</div>

	<div class="flex gap-4 border-b border-border pb-2.5">
		{#each Array(5) as _, i (i)}
			<Skeleton class="h-4 w-20" />
		{/each}
	</div>

	{#if tab === 'overview'}
		<div
			class="grid grid-cols-2 overflow-hidden rounded-xl border bg-card md:grid-cols-4 xl:grid-cols-7"
		>
			{#each Array(7) as _, i (i)}
				<div class="-mr-px -mb-px flex flex-col gap-2 border-r border-b px-4 py-3">
					<Skeleton class="h-3 w-16" />
					<Skeleton class="h-6 w-12" />
					<Skeleton class="h-3 w-20" />
				</div>
			{/each}
		</div>

		<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
			{@render cell('bars', 'col-span-12 xl:col-span-8')}
			{@render cell('map', 'col-span-12 xl:col-span-4')}
			{@render cell('meters', 'col-span-12 lg:col-span-6', 4)}
			{@render cell('list', 'col-span-12 lg:col-span-6', 4)}
		</div>
	{:else if tab === 'web-assets'}
		<div class="overflow-hidden rounded-xl border bg-card" bind:clientWidth={tableWidth}>
			<div class="flex gap-4 border-b px-4 py-3">
				{#each ['w-12', 'w-16', 'w-14'] as w (w)}
					<Skeleton class="h-4 {w}" />
				{/each}
			</div>
			<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
				<Skeleton class="h-9 min-w-[min(100%,16rem)] flex-1" />
				<Skeleton class="h-9 w-32" />
				<Skeleton class="size-9" />
				<Skeleton class="size-9" />
			</div>
			<TableSkeleton lead={ASSET_LEAD_COLUMNS} columns={assetColumns} />
		</div>
	{:else}
		<div class="overflow-hidden rounded-xl border bg-card">
			<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
				<Skeleton class="h-9 w-64 max-w-full" />
				<Skeleton class="ml-auto size-8" />
			</div>
			<div class="flex flex-col gap-3 px-4 py-4">
				{#each Array(6) as _, i (i)}
					<div class="grid grid-cols-[6rem_minmax(0,1fr)] gap-4 sm:grid-cols-[8rem_minmax(0,1fr)]">
						<Skeleton class="h-3.5 w-16" />
						<Skeleton class="h-3.5 w-72 max-w-full" />
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>
