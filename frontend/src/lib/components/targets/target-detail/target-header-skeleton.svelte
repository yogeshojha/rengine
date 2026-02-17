<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
</script>

<div class="space-y-4">
	<div class="flex items-start justify-between">
		<div class="space-y-3">
			<div class="flex items-center gap-3">
				<Skeleton class="h-10 w-10 rounded-lg" />
				<div class="space-y-2">
					<Skeleton class="h-7 w-72" />
					<Skeleton class="h-4 w-40" />
				</div>
			</div>
			<div class="flex gap-2">
				<Skeleton class="h-5 w-16 rounded-full" />
				<Skeleton class="h-5 w-24 rounded-full" />
				<Skeleton class="h-5 w-20 rounded-full" />
			</div>
			<div class="flex gap-2 items-center">
				<Skeleton class="h-5 w-24 rounded-full" />
				<Skeleton class="h-5 w-28 rounded-full" />
				<Skeleton class="h-5 w-24 rounded-full" />
				<Skeleton class="h-4 w-px" />
				<Skeleton class="h-4 w-32" />
				<Skeleton class="h-4 w-28" />
			</div>
		</div>
		<div class="flex gap-2">
			<Skeleton class="h-9 w-20" />
			<Skeleton class="h-9 w-9" />
			<Skeleton class="h-9 w-9" />
		</div>
	</div>
	<Skeleton class="h-10 w-96" />
</div>
