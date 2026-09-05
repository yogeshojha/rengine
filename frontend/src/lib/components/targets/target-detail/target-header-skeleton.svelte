<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
</script>

<div class="flex flex-col gap-5">
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
	<Skeleton class="h-10 w-96" />
	<Skeleton class="h-72 w-full" />
</div>
