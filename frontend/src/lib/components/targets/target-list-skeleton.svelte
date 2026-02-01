<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';

	interface Props {
		count?: number;
	}

	// number of Skeleton to show
	let { count = 5 }: Props = $props();
</script>

<div class="divide-y divide-border/50">
	{#each Array(count) as _, i}
		<div class="flex items-center gap-3 px-4 py-3">
			<Skeleton class="h-4 w-4 rounded" />
			<div class="w-[240px] space-y-1.5">
				<Skeleton class="h-4 w-48" />
				<Skeleton class="h-3 w-24" />
			</div>
			<div class="w-[120px]">
				<Skeleton class="h-5 w-20 rounded-full" />
			</div>
			<div class="hidden md:flex flex-1 min-w-[180px]">
				<Skeleton class="h-6 w-20 rounded-full" />
			</div>
			<div class="hidden lg:flex flex-1 min-w-[200px] gap-1.5">
				<Skeleton class="h-6 w-16 rounded-full" />
				<Skeleton class="h-6 w-14 rounded-full" />
			</div>
			<Skeleton class="hidden sm:block h-3 w-16 w-[80px]" />
			<div class="flex gap-1">
				<Skeleton class="h-8 w-8 rounded" />
				<Skeleton class="h-8 w-8 rounded" />
			</div>
		</div>
	{/each}
</div>
