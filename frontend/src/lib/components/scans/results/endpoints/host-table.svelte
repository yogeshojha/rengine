<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import ListHeader from '../table/list-header.svelte';
	import ResultsPagination from '../table/results-pagination.svelte';
	import HostRow from './host-row.svelte';
	import { HOST_LEAD_COLUMNS } from './columns';
	import type { TableColumn } from '../table/columns';
	import type { FolderChip, HostPage, TreeNode } from '$lib/utilities/endpoints';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		page: HostPage | null;
		loading?: boolean;
		searching?: boolean;
		terms?: string[];
		columns: TableColumn[];
		pad?: string;
		cursor?: number;
		sortKey: string;
		sortDir: 1 | -1;
		connectors?: Connector[];
		catalog?: ConnectorSpec[];
		onSort: (key: string) => void;
		onPage: (page: number) => void;
		onEnter: (host: string) => void;
		onEnterFolder: (host: string, chip: FolderChip) => void;
		onCopy: (node: TreeNode) => void;
		onWordlist: (node: TreeNode) => void;
		onList: (node: TreeNode) => void;
		onVerify?: (node: TreeNode) => void;
		onSend?: (node: TreeNode, connectorId: string) => void;
		onShowRootOnly?: () => void;
	}

	let {
		page,
		loading = false,
		searching = false,
		terms = [],
		columns,
		pad = 'py-3',
		cursor = -1,
		sortKey,
		sortDir,
		connectors = [],
		catalog = [],
		onSort,
		onPage,
		onEnter,
		onEnterFolder,
		onCopy,
		onWordlist,
		onList,
		onVerify,
		onSend,
		onShowRootOnly
	}: Props = $props();

	let lead = $derived(
		searching
			? HOST_LEAD_COLUMNS.map((c) => (c.key === 'endpoints' ? { ...c, label: 'Matches' } : c))
			: HOST_LEAD_COLUMNS
	);
	let pending = $derived(loading && !page);
</script>

<ScrollArea orientation="horizontal">
	<ListHeader {lead} {columns} {sortKey} {sortDir} {onSort} />
	<div class="transition-opacity {loading && !pending ? 'opacity-60' : ''}">
		{#if pending}
			<div class="divide-y divide-border/50">
				{#each Array(8) as _, i (i)}
					<div class="flex items-center gap-3 px-4 py-3">
						<Skeleton class="h-9 flex-1" />
						<Skeleton class="hidden h-5 w-24 sm:block" />
						<Skeleton class="hidden h-5 w-40 sm:block" />
					</div>
				{/each}
			</div>
		{:else if page}
			{#each page.items as node, i (node.key)}
				<div data-host-row-index={i}>
					<HostRow
						{node}
						{columns}
						{terms}
						{pad}
						{searching}
						{connectors}
						{catalog}
						focused={cursor === i}
						{onEnter}
						{onEnterFolder}
						{onCopy}
						{onWordlist}
						{onList}
						{onVerify}
						{onSend}
					/>
				</div>
			{/each}
		{/if}
	</div>
</ScrollArea>

{#if page && (page.root_only > 0 || page.total > page.size)}
	<div
		class="flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-4 py-2 text-xs text-muted-foreground"
	>
		{#if page.root_only > 0 && onShowRootOnly}
			<span>
				{page.root_only.toLocaleString()}
				{page.root_only === 1 ? 'host has' : 'hosts have'} only a root page.
			</span>
			<button
				type="button"
				class="rounded-sm text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				onclick={onShowRootOnly}
			>
				Show {page.root_only === 1 ? 'it' : 'them'}
			</button>
		{/if}
		{#if page.total > page.size}
			<div class="ml-auto -my-2 -mr-4">
				<ResultsPagination
					total={page.total}
					page={page.page - 1}
					pageSize={page.size}
					noun="host"
					plural="hosts"
					onPage={(p) => onPage(p + 1)}
				/>
			</div>
		{/if}
	</div>
{/if}
