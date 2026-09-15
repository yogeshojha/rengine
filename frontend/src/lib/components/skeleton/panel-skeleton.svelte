<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';

	interface Props {
		rows?: number;
		stats?: boolean;
		meter?: boolean;
		class?: string;
	}

	let { rows = 6, stats = false, meter = false, class: className = '' }: Props = $props();

	const WIDTH = ['w-56', 'w-44', 'w-64', 'w-48', 'w-52'];
</script>

<div class="space-y-4 py-1 {className}" aria-busy="true">
	<div class="flex items-center justify-between gap-3">
		<Skeleton class="h-4 w-40" />
		<Skeleton class="h-4 w-20" />
	</div>

	{#if stats}
		<div class="flex flex-wrap items-center gap-3">
			{#each Array(3) as _, i (i)}
				<Skeleton class="h-4 w-24" />
			{/each}
		</div>
	{/if}

	{#if meter}
		<Skeleton class="h-2 w-full rounded-full" />
	{/if}

	<div class="flex flex-col gap-2">
		{#each Array(rows) as _, i (i)}
			<div class="flex items-center gap-3 rounded-lg border border-border/50 px-3 py-2">
				<Skeleton class="size-4 shrink-0 rounded" />
				<div class="flex min-w-0 flex-1 flex-col gap-1.5">
					<Skeleton class="h-4 {WIDTH[i % WIDTH.length]} max-w-full" />
					<Skeleton class="h-3 w-24" />
				</div>
				<Skeleton class="hidden h-4 w-16 shrink-0 sm:block" />
			</div>
		{/each}
	</div>
</div>
