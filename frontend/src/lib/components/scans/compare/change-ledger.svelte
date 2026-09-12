<script lang="ts">
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import EyeOff from '@lucide/svelte/icons/eye-off';
	import ListFilter from '@lucide/svelte/icons/list-filter';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import ChangeRowItem from './change-row.svelte';
	import type { ChangeRow } from '$lib/types/compare';

	interface Props {
		rows: ChangeRow[];
		total: number;
		page: number;
		size: number;
		loading: boolean;
		digest: boolean;
		showDimension: boolean;
		covered: boolean;
		notCoveredNote: string;
		anyVerbOn: boolean;
		selectedKey: string | null;
		noun: string;
		nounPlural: string;
		onOpen: (row: ChangeRow) => void;
		onPage: (page: number) => void;
	}

	let {
		rows,
		total,
		page,
		size,
		loading,
		digest,
		showDimension,
		covered,
		notCoveredNote,
		anyVerbOn,
		selectedKey,
		noun,
		nounPlural,
		onOpen,
		onPage
	}: Props = $props();
</script>

{#if loading && !rows.length}
	<div class="flex flex-col gap-px p-4 sm:p-5">
		{#each [0, 1, 2, 3, 4, 5] as i (i)}
			<Skeleton class="h-14" />
		{/each}
	</div>
{:else if !covered}
	<EmptyState
		icon={EyeOff}
		title="Not scanned"
		description={notCoveredNote}
		class="m-4 sm:m-5"
		compact
	/>
{:else if !anyVerbOn}
	<EmptyState icon={ListFilter} title="No change kinds selected" class="m-4 sm:m-5" compact />
{:else if !rows.length}
	<EmptyState icon={CheckCheck} title="Nothing changed" class="m-4 sm:m-5" compact />
{:else}
	<div class="flex flex-col">
		{#each rows as row (row.dimension + row.key)}
			<ChangeRowItem
				{row}
				{showDimension}
				selected={selectedKey === row.dimension + row.key}
				{onOpen}
			/>
		{/each}
	</div>

	{#if digest}
		{#if rows.length < total}
			<p class="border-t bg-muted/20 px-4 py-3 text-xs text-muted-foreground sm:px-5">
				{rows.length.toLocaleString()} of {total.toLocaleString()} changes, highest signal first.
			</p>
		{:else}
			<p class="border-t bg-muted/20 px-4 py-3 text-xs text-muted-foreground sm:px-5">
				{total.toLocaleString()}
				{total === 1 ? 'change' : 'changes'}, highest signal first.
			</p>
		{/if}
	{:else}
		<ResultsPagination
			{total}
			page={page - 1}
			pageSize={size}
			{noun}
			plural={nounPlural}
			onPage={(p) => onPage(p + 1)}
		/>
	{/if}
{/if}
