<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CellSkeleton from '$lib/components/skeleton/cell-skeleton.svelte';
	import type { SkeletonShape } from '$lib/components/skeleton/shapes';
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
		<div class="flex items-start gap-3">
			<Skeleton class="size-10 rounded-lg" />
			<div class="flex flex-col gap-2">
				<Skeleton class="h-6 w-56" />
				<Skeleton class="h-4 w-80" />
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
</div>
