<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CellSkeleton from '$lib/components/skeleton/cell-skeleton.svelte';
	import { widgetSpec } from '$lib/config/dashboard-widgets';
	import { dashboardLayout } from '$lib/stores/dashboard-layout.svelte';

	const show = (id: string) => dashboardLayout.visible(id);
	const shape = (id: string) => widgetSpec(id)?.skeleton ?? 'text';
</script>

{#snippet cell(id: string, width: string, rows = 5)}
	<section class="-mr-px -mb-px flex min-w-0 flex-col border-r border-b bg-card {width}">
		<div class="flex items-start justify-between gap-3 px-4 pt-3.5">
			<Skeleton class="h-5 w-32" />
			<Skeleton class="h-3.5 w-12" />
		</div>
		<div class="flex min-h-0 flex-1 flex-col px-4 pt-3 pb-4">
			<CellSkeleton shape={shape(id)} {rows} />
		</div>
		<div class="mt-auto flex items-center gap-3 border-t px-4 py-2">
			<Skeleton class="h-3 w-24" />
		</div>
	</section>
{/snippet}

<div class="flex flex-col gap-4" aria-busy="true">
	<div
		class="grid grid-cols-2 overflow-hidden rounded-xl border bg-card md:grid-cols-4 xl:grid-cols-7"
	>
		{#each Array(7) as _, i (i)}
			<div class="-mr-px -mb-px flex min-w-0 flex-col gap-1 border-r border-b px-4 py-3">
				<Skeleton class="h-3 w-16" />
				<Skeleton class="h-6 w-12" />
				<Skeleton class="h-4 w-20" />
				<Skeleton class="mt-1 h-5 w-full" />
			</div>
		{/each}
	</div>

	<div class="grid grid-cols-12 overflow-hidden rounded-xl border bg-card">
		{#if show('funnel')}{@render cell('funnel', 'col-span-12 xl:col-span-8')}{/if}
		{#if show('geo')}{@render cell('geo', 'col-span-12 lg:col-span-6 xl:col-span-4')}{/if}
		{#if show('changes')}{@render cell('changes', 'col-span-12 xl:col-span-8')}{/if}
		{#if show('inventory')}{@render cell(
				'inventory',
				'col-span-12 lg:col-span-6 xl:col-span-4',
				6
			)}{/if}
	</div>

	<div class="overflow-hidden rounded-xl border bg-card">
		{#if show('board')}
			<div class="grid">{@render cell('board', '')}</div>
		{/if}
		<div class="grid grid-cols-[repeat(auto-fit,minmax(16rem,1fr))]">
			{#if show('findings-trend')}{@render cell('findings-trend', 'xl:col-span-2')}{/if}
			{#if show('exploitation')}{@render cell('exploitation', '', 4)}{/if}
			{#if show('evidence')}{@render cell('evidence', '', 4)}{/if}
		</div>
	</div>

	<div class="overflow-hidden rounded-xl border bg-card">
		<div class="grid grid-cols-[repeat(auto-fit,minmax(22rem,1fr))]">
			{#if show('runs')}{@render cell('runs', '')}{/if}
			{#if show('software')}{@render cell('software', '', 5)}{/if}
		</div>
		<div class="grid grid-cols-[repeat(auto-fit,minmax(16rem,1fr))]">
			{#if show('services')}{@render cell('services', '', 4)}{/if}
			{#if show('tech')}{@render cell('tech', '', 5)}{/if}
			{#if show('hosting')}{@render cell('hosting', '', 4)}{/if}
		</div>
	</div>
</div>
