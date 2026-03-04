<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
	{#each { length: 2 } as _}
		<div class="rounded-lg border border-border bg-card overflow-hidden">
			<div class="flex items-center justify-between px-3 py-2 border-b border-border/50">
				<div class="flex items-center gap-2">
					<Skeleton class="h-1.5 w-1.5 rounded-full" />
					<Skeleton class="h-3 w-16" />
				</div>
				<Skeleton class="h-5 w-5 rounded" />
			</div>
			<div class="p-3 space-y-2">
				{#each { length: 5 } as _}
					<div class="flex items-center justify-between">
						<Skeleton class="h-3 w-20" />
						<Skeleton class="h-3 w-28" />
					</div>
				{/each}
			</div>
		</div>
	{/each}

	<div class="lg:col-span-2 rounded-lg border border-border bg-card overflow-hidden">
		<div class="flex items-center justify-between px-3 py-2 border-b border-border/50">
			<div class="flex items-center gap-2">
				<Skeleton class="h-1.5 w-1.5 rounded-full" />
				<Skeleton class="h-3 w-20" />
			</div>
			<Skeleton class="h-5 w-5 rounded" />
		</div>
		<div class="p-3 space-y-1.5">
			{#each { length: 4 } as _}
				<Skeleton class="h-7 w-full rounded" />
			{/each}
		</div>
	</div>
</div>
