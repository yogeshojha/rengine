<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';

	interface Props {
		count?: number;
	}

	let { count = 5 }: Props = $props();
</script>

<div class="divide-y divide-border/50">
	{#each Array(count) as _, i}
		<div class="flex items-center gap-4 px-4 py-3">
			<div class="flex-1 space-y-2">
				<Skeleton class="h-4 w-48" />
				<Skeleton class="h-3 w-32" />
			</div>
			<div class="hidden md:flex gap-1.5">
				<Skeleton class="h-6 w-20 rounded-full" />
			</div>
			<div class="hidden lg:flex gap-1.5">
				<Skeleton class="h-6 w-16 rounded-full" />
				<Skeleton class="h-6 w-14 rounded-full" />
			</div>
			<Skeleton class="hidden sm:block h-3 w-16" />
			<Skeleton class="h-8 w-8 rounded" />
		</div>
	{/each}
</div>
