<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';

	interface Props {
		rows?: number;
		avatar?: string | null;
		trailing?: string | null;
		class?: string;
	}

	let {
		rows = 8,
		avatar = 'size-9 rounded-md',
		trailing = 'h-5 w-24 rounded-full',
		class: className = ''
	}: Props = $props();

	const WIDTH = ['w-64', 'w-48', 'w-56'];
</script>

<div class={className} aria-busy="true">
	{#each Array(rows) as _, i (i)}
		<div class="flex w-full items-center gap-3 border-b px-4 py-3 last:border-b-0">
			{#if avatar}
				<Skeleton class="shrink-0 {avatar}" />
			{/if}
			<div class="flex min-w-0 flex-1 flex-col gap-1.5">
				<Skeleton class="h-4 max-w-full {WIDTH[i % WIDTH.length]}" />
				<Skeleton class="h-3 w-40 max-w-full" />
			</div>
			{#if trailing}
				<Skeleton class="hidden shrink-0 sm:block {trailing}" />
			{/if}
		</div>
	{/each}
</div>
