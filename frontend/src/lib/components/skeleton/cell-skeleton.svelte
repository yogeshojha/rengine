<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import type { SkeletonShape } from './shapes';

	interface Props {
		shape?: SkeletonShape;
		rows?: number;
		class?: string;
	}

	let { shape = 'text', rows = 5, class: className = '' }: Props = $props();

	const BAR_HEIGHT = [
		'h-10',
		'h-20',
		'h-14',
		'h-24',
		'h-16',
		'h-28',
		'h-12',
		'h-20',
		'h-24',
		'h-14'
	];
	const METER = ['w-3/4', 'w-1/2', 'w-2/3', 'w-1/3', 'w-5/6'];
	const LABEL = ['w-32', 'w-24', 'w-40', 'w-28', 'w-36', 'w-20'];
</script>

<div class="flex min-w-0 flex-1 flex-col gap-3 {className}" aria-busy="true">
	{#if shape === 'bars'}
		<div class="flex h-32 items-end gap-1.5">
			{#each Array(12) as _, i (i)}
				<Skeleton class="flex-1 {BAR_HEIGHT[i % BAR_HEIGHT.length]}" />
			{/each}
		</div>
		<div class="flex justify-between">
			<Skeleton class="h-3 w-16" />
			<Skeleton class="h-3 w-16" />
		</div>
	{:else if shape === 'ranked'}
		{#each Array(rows) as _, i (i)}
			<div class="flex flex-col gap-1.5 px-2">
				<div class="flex items-baseline justify-between gap-3">
					<Skeleton class="h-4 {LABEL[i % LABEL.length]}" />
					<Skeleton class="h-3 w-8" />
				</div>
				<Skeleton class="h-1 {METER[i % METER.length]} rounded-full" />
			</div>
		{/each}
	{:else if shape === 'list'}
		{#each Array(rows) as _, i (i)}
			<div class="flex items-center justify-between gap-3">
				<Skeleton class="h-4 {LABEL[i % LABEL.length]}" />
				<Skeleton class="h-4 w-10" />
			</div>
		{/each}
	{:else if shape === 'meters'}
		{#each Array(rows) as _, i (i)}
			<div class="flex flex-col gap-1.5">
				<div class="flex items-baseline justify-between gap-3">
					<Skeleton class="h-3.5 {LABEL[i % LABEL.length]}" />
					<Skeleton class="h-3 w-12" />
				</div>
				<Skeleton class="h-1.5 w-full rounded-full" />
			</div>
		{/each}
	{:else if shape === 'donut'}
		<div class="flex items-center gap-6">
			<Skeleton class="size-28 shrink-0 rounded-full" />
			<div class="flex min-w-0 flex-1 flex-col gap-2">
				{#each Array(4) as _, i (i)}
					<div class="flex items-center gap-2">
						<Skeleton class="size-2.5 shrink-0 rounded-[2px]" />
						<Skeleton class="h-3.5 {LABEL[i % LABEL.length]}" />
					</div>
				{/each}
			</div>
		</div>
	{:else if shape === 'map'}
		<Skeleton class="h-48 w-full" />
		<div class="flex flex-wrap gap-2">
			{#each Array(4) as _, i (i)}
				<Skeleton class="h-5 w-20 rounded-full" />
			{/each}
		</div>
	{:else if shape === 'stat'}
		<div class="flex flex-wrap gap-6">
			{#each Array(rows) as _, i (i)}
				<div class="flex flex-col gap-2">
					<Skeleton class="h-7 w-16" />
					<Skeleton class="h-3 w-20" />
				</div>
			{/each}
		</div>
	{:else if shape === 'board'}
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<div class="flex flex-col gap-2 rounded-lg border p-3">
					<Skeleton class="h-3.5 w-20" />
					<Skeleton class="h-4 w-full" />
					<Skeleton class="h-4 w-2/3" />
				</div>
			{/each}
		</div>
	{:else}
		<Skeleton class="h-5 w-2/3" />
		<Skeleton class="h-24 w-full" />
		<Skeleton class="h-5 w-1/2" />
	{/if}
</div>
