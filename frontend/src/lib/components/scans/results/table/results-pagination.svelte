<script lang="ts">
	import * as Pagination from '$lib/components/ui/pagination';
	import PageSizeSelector from '$lib/components/targets/page-size-selector.svelte';

	interface Props {
		total: number;
		page: number;
		pageSize: number;
		capped?: boolean;
		noun?: string;
		plural?: string;
		onPage: (page: number) => void;
		onPageSize?: (size: number) => void;
	}

	let {
		total,
		page,
		pageSize,
		capped = false,
		noun = 'host',
		plural = '',
		onPage,
		onPageSize
	}: Props = $props();

	const SIZES = [25, 50, 100, 200];

	let from = $derived(total === 0 ? 0 : page * pageSize + 1);
	let to = $derived(Math.min((page + 1) * pageSize, total));
</script>

<div class="flex flex-wrap items-center justify-between gap-3 border-t bg-muted/20 px-4 py-3">
	<div class="flex flex-wrap items-center gap-4">
		<span class="text-xs text-muted-foreground tabular-nums">
			Showing {from.toLocaleString()}–{to.toLocaleString()} of {total.toLocaleString()}{capped
				? '+'
				: ''}
			{total === 1 ? noun : plural || `${noun}s`}
		</span>
		{#if onPageSize}
			<PageSizeSelector {pageSize} options={SIZES} onPageSizeChange={onPageSize} />
		{/if}
	</div>
	{#if total > pageSize}
		<Pagination.Root
			count={total}
			perPage={pageSize}
			page={page + 1}
			onPageChange={(p) => onPage(p - 1)}
			class="mx-0 w-auto"
		>
			{#snippet children({ pages, currentPage })}
				<Pagination.Content>
					<Pagination.Item><Pagination.Previous /></Pagination.Item>
					{#each pages as p (p.key)}
						{#if p.type === 'ellipsis'}
							<Pagination.Item><Pagination.Ellipsis /></Pagination.Item>
						{:else}
							<Pagination.Item>
								<Pagination.Link page={p} isActive={currentPage === p.value}>
									{p.value}
								</Pagination.Link>
							</Pagination.Item>
						{/if}
					{/each}
					<Pagination.Item><Pagination.Next /></Pagination.Item>
				</Pagination.Content>
			{/snippet}
		</Pagination.Root>
	{/if}
</div>
