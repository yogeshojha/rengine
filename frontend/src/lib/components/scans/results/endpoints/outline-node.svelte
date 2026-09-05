<script lang="ts">
	import { untrack } from 'svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import FolderRow from './folder-row.svelte';
	import EndpointRow from './endpoint-row.svelte';
	import MergedLeafRow from './merged-leaf-row.svelte';
	import Self from './outline-node.svelte';
	import {
		GUIDE_WIDTH,
		LEAF_PAGE,
		AUTO_OPEN_ROWS,
		nodeCost,
		type OutlineContext
	} from './outline-context';
	import { endpointsApi } from '$lib/api/scan-results';
	import {
		leafToEndpoint,
		type EndpointRead,
		type MergedLeaf,
		type TreeLeaf,
		type TreeNode
	} from '$lib/utilities/endpoints';

	interface Props {
		node: TreeNode;
		depth: number;
		ctx: OutlineContext;
		headless?: boolean;
		parentKey?: string;
	}

	let { node, depth, ctx, headless = false, parentKey = '' }: Props = $props();
	let childParent = $derived(headless ? parentKey : node.key);

	let open = $derived(headless || ctx.expanded.has(node.key));
	let childDepth = $derived(headless ? depth : depth + 1);

	// a host arrives without its folders; they load the first time it opens
	let lazyChildren = $state<TreeNode[] | null>(null);
	let lazyLoading = $state(false);
	let lazySig = '';
	let lazyReq = 0;
	let children = $derived(node.lazy ? (lazyChildren ?? []) : node.children);
	let childrenKnown = $derived(!node.lazy || lazyChildren !== null);

	let folders = $derived(children.filter((c) => c.kind !== 'leaf'));
	let leafNodes = $derived(children.filter((c) => c.kind === 'leaf'));
	let ordered = $derived.by(() => {
		if (ctx.filter.sort !== 'path') return { folders, leafNodes };
		const dir = ctx.filter.direction === 'desc' ? -1 : 1;
		const byName = (a: TreeNode, b: TreeNode) => dir * a.name.localeCompare(b.name);
		return { folders: [...folders].sort(byName), leafNodes: [...leafNodes].sort(byName) };
	});

	let hostFilter = $derived({
		...ctx.filter,
		host: node.host,
		dir_path: null,
		subtree: true,
		page: 1,
		size: 1
	});
	let hostSig = $derived(JSON.stringify(hostFilter));

	async function loadHost() {
		const my = ++lazyReq;
		lazyLoading = true;
		try {
			const res = await endpointsApi.tree(ctx.projectId, ctx.scanId, 'host', hostFilter);
			if (my !== lazyReq) return;
			lazyChildren = res.nodes[0]?.children ?? [];
		} catch {
			if (my === lazyReq) {
				lazyChildren = [];
				lazySig = '';
			}
		} finally {
			if (my === lazyReq) lazyLoading = false;
		}
	}

	$effect(() => {
		void hostSig;
		if (!node.lazy || !open) return;
		if (hostSig === lazySig) return;
		lazySig = hostSig;
		untrack(() => void loadHost());
	});

	// a search opens this node only while the opened rows still fit the screen budget
	$effect(() => {
		const budget = ctx.budget;
		if (!budget.enabled || headless || budget.decided.has(node.key)) return;
		if (node.kind === 'leaf') return;
		if (!node.lazy && !node.children.length && node.direct_count === 0) return;
		const cost = nodeCost(node, node.lazy ? [] : node.children);
		budget.decided.add(node.key);
		if (budget.used + cost <= AUTO_OPEN_ROWS) {
			budget.used += cost;
			untrack(() => ctx.expanded.add(node.key));
		}
	});

	let leaves = $state<EndpointRead[]>([]);
	let merged = $state<MergedLeaf[]>([]);
	let total = $state(0);
	let page = $state(1);
	let loading = $state(false);
	let loadedSig = '';
	let req = 0;

	let leafFilter = $derived({
		...ctx.filter,
		host: ctx.merged ? null : node.host,
		dir_path: node.path,
		subtree: false
	});
	let sig = $derived(JSON.stringify(leafFilter) + (ctx.merged ? '|m' : '|h'));

	async function load(nextPage: number) {
		const my = ++req;
		loading = true;
		try {
			if (ctx.merged) {
				const res = await endpointsApi.mergedLeaves(ctx.projectId, ctx.scanId, leafFilter);
				if (my !== req) return;
				merged = res.items;
				total = res.total;
			} else {
				const res = await endpointsApi.search(ctx.projectId, ctx.scanId, {
					...leafFilter,
					page: nextPage,
					size: LEAF_PAGE
				});
				if (my !== req) return;
				leaves = nextPage === 1 ? res.items : [...leaves, ...res.items];
				total = res.total;
				page = nextPage;
			}
		} catch {
			if (my === req) {
				leaves = [];
				merged = [];
				total = 0;
				loadedSig = '';
			}
		} finally {
			if (my === req) loading = false;
		}
	}

	$effect(() => {
		void sig;
		if (!open || node.direct_count === 0) return;
		if (sig === loadedSig) return;
		loadedSig = sig;
		untrack(() => void load(1));
	});

	let remaining = $derived(Math.max(0, total - leaves.length));

	function leafLabel(e: EndpointRead): string | undefined {
		return e.filename === null && e.path !== node.path ? e.path : undefined;
	}

	type Row =
		| { kind: 'node'; key: string; node: TreeNode; leaf: TreeLeaf; endpoint: EndpointRead }
		| { kind: 'leaf'; key: string; endpoint: EndpointRead };

	// interest, then input, then answering, then name: the same order the server gives leaves
	function rank(e: EndpointRead, name: string): [number, number, number, number, string] {
		const ok = e.status_code !== null && e.status_code >= 200 && e.status_code < 300;
		return [
			e.interest.length ? 0 : 1,
			e.param_count ? 0 : 1,
			e.is_probed ? 0 : 1,
			ok ? 0 : 1,
			name
		];
	}
	function rowName(r: Row): string {
		return r.kind === 'node' ? r.node.name : (r.endpoint.filename ?? '/');
	}
	function compare(a: Row, b: Row): number {
		const ra = rank(a.endpoint, rowName(a));
		const rb = rank(b.endpoint, rowName(b));
		for (let i = 0; i < 4; i++) {
			if (ra[i] !== rb[i]) return (ra[i] as number) - (rb[i] as number);
		}
		return (ra[4] as string).localeCompare(rb[4] as string);
	}
	let rows = $derived.by<Row[]>(() => {
		const nodes: Row[] = ordered.leafNodes
			.filter((c) => c.leaf)
			.map((c) => ({
				kind: 'node',
				key: c.key,
				node: c,
				leaf: c.leaf!,
				endpoint: leafToEndpoint(c.leaf!, ctx.scanId)
			}));
		const fetched: Row[] = leaves.map((e) => ({ kind: 'leaf', key: e.id, endpoint: e }));
		if (ctx.filter.sort === 'relevance') return [...fetched, ...nodes].sort(compare);
		if (ctx.filter.sort === 'path') {
			const dir = ctx.filter.direction === 'desc' ? -1 : 1;
			return [...fetched, ...nodes].sort((a, b) => dir * rowName(a).localeCompare(rowName(b)));
		}
		return [...fetched, ...nodes];
	});

	// a closed row says what is inside it while a search is on, so nothing has to be opened to see why it matched
	let hint = $derived.by(() => {
		if (node.kind === 'group') return `each has ${node.top_folders.join(', ')}`;
		if (!ctx.searching || open) return '';
		const names = node.lazy ? node.top_folders : node.children.map((c) => c.name);
		const count = node.lazy ? node.folders : node.children.length;
		if (!names.length) return '';
		const shown = names.slice(0, 3).join(', ');
		return count > 3 ? `in ${shown} +${count - 3}` : `in ${shown}`;
	});

	let skeletonRows = $derived(Math.min(Math.max(node.direct_count, node.folders, 1), 3));
</script>

{#if !headless}
	<FolderRow
		{node}
		{open}
		{depth}
		columns={ctx.columns}
		terms={ctx.terms}
		merged={ctx.merged}
		pad={ctx.pad}
		{hint}
		focused={ctx.focusedKey === node.key}
		unverified={node.unprobed}
		{parentKey}
		onToggle={() => ctx.toggle(node.key)}
		onCopy={() => ctx.copyBranch(node)}
		onWordlist={() => ctx.copyWordlist(node)}
		onOnly={() => ctx.onFilter(node.query)}
		onList={() => ctx.onShowInList(node.query)}
		onVerify={ctx.verifyBranch && node.kind !== 'group' && !ctx.merged
			? () => ctx.verifyBranch?.(node)
			: undefined}
	/>
{/if}

{#if open}
	{#if node.lazy && (lazyLoading || !childrenKnown)}
		{#each Array(skeletonRows) as _, i (i)}
			<div class="flex items-center gap-3 border-b px-4 py-3">
				{#each Array(childDepth) as _g, j (j)}
					<span class="{GUIDE_WIDTH} -ml-1.5 h-5 shrink-0 border-l border-border/70 ml-[7px]"
					></span>
				{/each}
				<Skeleton class="h-5 flex-1" />
				<Skeleton class="hidden h-5 w-16 sm:block" />
			</div>
		{/each}
	{:else}
		{#each ordered.folders as child (child.key)}
			<Self node={child} depth={childDepth} {ctx} parentKey={childParent} />
		{/each}

		{#if ctx.merged}
			{#each ordered.leafNodes as child (child.key)}
				{#if child.leaf}
					<EndpointRow
						endpoint={leafToEndpoint(child.leaf, ctx.scanId)}
						columns={ctx.columns.map((c) => c.key)}
						terms={ctx.terms}
						outline
						depth={childDepth}
						label={child.name}
						rowKey={child.key}
						parentKey={childParent}
						pad={ctx.pad}
						active={ctx.selectedId === child.leaf.id}
						focused={ctx.focusedKey === child.key}
						onOpen={() => ctx.openById(child.leaf!.id)}
						onFilter={ctx.onFilter}
					/>
				{/if}
			{/each}
		{:else}
			{#each rows as row (row.key)}
				<EndpointRow
					endpoint={row.endpoint}
					columns={ctx.columns.map((c) => c.key)}
					terms={ctx.terms}
					outline
					depth={childDepth}
					label={row.kind === 'node' ? row.node.name : leafLabel(row.endpoint)}
					rowKey={row.key}
					parentKey={childParent}
					pad={ctx.pad}
					active={ctx.selectedId === row.endpoint.id}
					focused={ctx.focusedKey === row.key}
					onOpen={row.kind === 'node' ? () => ctx.openById(row.endpoint.id) : ctx.openEndpoint}
					onFilter={ctx.onFilter}
				/>
			{/each}
		{/if}

		{#if node.direct_count > 0}
			{#if loading && leaves.length === 0 && merged.length === 0}
				{#each Array(Math.min(node.direct_count, 3)) as _, i (i)}
					<div class="flex items-center gap-3 border-b px-4 py-3">
						{#each Array(childDepth) as _g, j (j)}
							<span class="{GUIDE_WIDTH} -ml-1.5 h-5 shrink-0 border-l border-border/70 ml-[7px]"
							></span>
						{/each}
						<Skeleton class="h-5 flex-1" />
						<Skeleton class="hidden h-5 w-16 sm:block" />
					</div>
				{/each}
			{:else if ctx.merged}
				{#each merged as leaf (leaf.key)}
					<MergedLeafRow
						{leaf}
						depth={childDepth}
						columns={ctx.columns}
						terms={ctx.terms}
						pad={ctx.pad}
						parentKey={childParent}
						active={ctx.selectedId === leaf.sample_id}
						focused={ctx.focusedKey === leaf.key}
						onOpen={ctx.openMerged}
						onFilter={ctx.onFilter}
						onHost={ctx.onHost}
					/>
				{/each}
			{:else if remaining > 0}
				<div class="flex items-center gap-x-1.5 border-b px-4 py-2 text-xs">
					{#each Array(childDepth) as _g, j (j)}
						<span class="{GUIDE_WIDTH} -ml-1.5 h-5 shrink-0 border-l border-border/70 ml-[7px]"
						></span>
					{/each}
					<span class="size-4 shrink-0"></span>
					<button
						type="button"
						class="font-medium text-primary hover:underline disabled:opacity-60"
						disabled={loading}
						onclick={() => load(page + 1)}
					>
						{loading
							? 'Loading…'
							: `Show ${Math.min(remaining, LEAF_PAGE).toLocaleString()} more${
									node.kind === 'host' ? '' : ` in ${node.name}`
								}`}
					</button>
					<span class="text-muted-foreground">· {remaining.toLocaleString()} remaining</span>
				</div>
			{/if}
		{/if}
	{/if}
{/if}
