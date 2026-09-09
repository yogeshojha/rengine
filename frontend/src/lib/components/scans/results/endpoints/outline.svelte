<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';

	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import ListHeader from '../table/list-header.svelte';
	import OutlineNode from './outline-node.svelte';
	import { OUTLINE_LEAD_COLUMNS } from './columns';
	import {
		CRUMB_HEIGHT,
		OUTLINE_ROW_ATTR,
		type Crumb,
		type OpenBudget,
		type OutlineContext
	} from './outline-context';
	import type { TableColumn } from '../table/columns';
	import { endpointsApi } from '$lib/api/scan-results';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { copyBranch, copyWordlist, type BranchScope } from './branch-actions';
	import type {
		EndpointFilter,
		EndpointRead,
		EndpointTree,
		MergedLeaf,
		TreeNode
	} from '$lib/utilities/endpoints';
	import type { Connector, ConnectorSpec } from '$lib/types/connector';

	interface Props {
		projectId: string;
		scanId: string;
		tree?: EndpointTree | null;
		loading?: boolean;
		merged?: boolean;
		rooted?: boolean;
		embedded?: boolean;
		openKeys?: string[];
		filter: EndpointFilter;
		terms?: string[];
		columns: TableColumn[];
		pad?: string;
		active?: boolean;
		paused?: boolean;
		searching?: boolean;
		selectedId?: string | null;
		sortKey: string;
		sortDir: 1 | -1;
		connectors?: Connector[];
		catalog?: ConnectorSpec[];
		onSort: (key: string) => void;
		onOpen: (e: EndpointRead) => void;
		onFilter: (token: string) => void;
		onShowInList?: (token: string) => void;
		onHost: (host: string) => void;
		onExpandedChange?: (count: number) => void;
		onVerify?: (node: TreeNode) => void;
		onSend?: (node: TreeNode, connectorId: string) => void;
		edgeEl?: HTMLElement | null;
		onCrumbs?: (crumbs: Crumb[]) => void;
	}

	let {
		projectId,
		scanId,
		tree = null,
		loading = false,
		merged = false,
		rooted = false,
		embedded = false,
		openKeys = [],
		filter,
		terms = [],
		columns,
		pad = 'py-3',
		active = true,
		paused = false,
		searching = false,
		selectedId = null,
		sortKey,
		sortDir,
		connectors = [],
		catalog = [],
		onSort,
		onOpen,
		onFilter,
		onShowInList,
		onHost,
		onExpandedChange,
		onVerify,
		onSend,
		edgeEl = null,
		onCrumbs
	}: Props = $props();

	const REMEMBER_CAP = 400;

	const expanded = new SvelteSet<string>();
	let budget = $state<OpenBudget>({ enabled: false, used: 0, decided: new SvelteSet<string>() });
	let autoKey = '';
	let focusedKey = $state('');
	let container = $state<HTMLElement | null>(null);

	let roots = $derived(tree?.nodes ?? []);
	// a tree always has exactly one root here, and the root is never a row: the header above it is
	let headless = $derived(merged || embedded || rooted);
	let shownRoots = $derived(headless ? roots.slice(0, 1) : roots);
	let rootName = $derived(roots[0]?.name ?? '');
	let rememberKey = $derived(
		embedded
			? ''
			: `${STORAGE_KEYS.endpointsExpanded}:${scanId}:${merged ? 'merged' : `host:${rootName}`}`
	);

	function remembered(): string[] {
		if (!rememberKey) return [];
		try {
			const raw = sessionStorage.getItem(rememberKey);
			return raw ? (JSON.parse(raw) as string[]) : [];
		} catch {
			return [];
		}
	}
	function remember() {
		if (!rememberKey || searching) return;
		try {
			sessionStorage.setItem(rememberKey, JSON.stringify([...expanded].slice(0, REMEMBER_CAP)));
		} catch {
			// session memory is a convenience
		}
	}

	// at rest nothing opens on its own; a search hands out a screen budget and branches open while it lasts
	$effect(() => {
		const key =
			roots.map((n) => n.key).join('|') + (searching ? '|s' : '') + (headless ? '|h' : '');
		if (!tree || key === autoKey) return;
		autoKey = key;
		expanded.clear();
		focusedKey = '';
		budget = { enabled: searching, used: 0, decided: new SvelteSet<string>() };
		if (!searching) {
			const keys = new Set(roots.map((n) => n.key));
			for (const k of untrack(remembered)) {
				if (keys.has(k) || [...keys].some((root) => k.startsWith(root))) expanded.add(k);
			}
		}
		for (const k of untrack(() => openKeys)) openWithAncestors(k);
	});

	// a folder chip on the host row lands here already open, through whatever group folds it
	$effect(() => {
		const keys = openKeys;
		if (!tree) return;
		untrack(() => {
			for (const k of keys) openWithAncestors(k);
		});
	});

	function pathTo(nodes: TreeNode[], key: string, trail: string[] = []): string[] | null {
		for (const n of nodes) {
			if (n.key === key) return [...trail, n.key];
			const found = pathTo(n.children, key, [...trail, n.key]);
			if (found) return found;
		}
		return null;
	}
	function openWithAncestors(key: string) {
		for (const k of pathTo(roots, key) ?? [key]) expanded.add(k);
	}

	$effect(() => {
		onExpandedChange?.(expanded.size);
		untrack(remember);
	});

	function toggle(key: string) {
		if (expanded.has(key)) expanded.delete(key);
		else expanded.add(key);
	}

	export function collapseAll() {
		expanded.clear();
		budget = { enabled: false, used: 0, decided: new SvelteSet<string>() };
	}

	async function openById(id: string) {
		try {
			onOpen(await endpointsApi.detail(projectId, scanId, id));
		} catch {
			toast.error('That endpoint could not be loaded.');
		}
	}

	function openMerged(leaf: MergedLeaf) {
		void openById(leaf.sample_id);
	}

	let branchScope = $derived<BranchScope>({ projectId, scanId, filter, merged });

	let ctx = $derived<OutlineContext>({
		projectId,
		scanId,
		merged,
		searching,
		filter,
		columns,
		terms,
		pad,
		expanded,
		budget,
		focusedKey,
		selectedId,
		connectors,
		catalog,
		toggle,
		openEndpoint: onOpen,
		openById,
		openMerged,
		onFilter,
		onShowInList: onShowInList ?? onFilter,
		onHost,
		copyBranch: (node) => copyBranch(branchScope, node),
		copyWordlist: (node) => copyWordlist(branchScope, node),
		verifyBranch: onVerify,
		sendBranch: onSend
	});

	function rows(): HTMLElement[] {
		return container
			? Array.from(container.querySelectorAll<HTMLElement>(`[${OUTLINE_ROW_ATTR}]`))
			: [];
	}
	function move(step: 1 | -1) {
		const all = rows();
		if (!all.length) return;
		const at = all.findIndex((el) => el.getAttribute(OUTLINE_ROW_ATTR) === focusedKey);
		const next = Math.min(all.length - 1, Math.max(0, at + step));
		const el = all[next];
		focusedKey = el.getAttribute(OUTLINE_ROW_ATTR) ?? '';
		el.scrollIntoView({ block: 'nearest' });
	}
	function focusedRow(): HTMLElement | null {
		return rows().find((el) => el.getAttribute(OUTLINE_ROW_ATTR) === focusedKey) ?? null;
	}
	function onKey(e: KeyboardEvent) {
		if (!active || paused || e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		if (e.key === 'j' || e.key === 'ArrowDown') {
			e.preventDefault();
			move(1);
		} else if (e.key === 'k' || e.key === 'ArrowUp') {
			e.preventDefault();
			move(-1);
		} else if (e.key === 'Escape') {
			focusedKey = '';
			typed = '';
		} else if (e.key.length === 1 && /[a-z0-9._-]/i.test(e.key) && !e.shiftKey) {
			e.preventDefault();
			typeAhead(e.key);
		} else if (focusedKey) {
			const el = focusedRow();
			if (!el) return;
			const isFolder = el.getAttribute('data-outline-kind') === 'folder';
			if (e.key === 'Enter') {
				e.preventDefault();
				if (isFolder) toggle(focusedKey);
				else el.click();
			} else if (e.key === 'ArrowRight' && isFolder && !expanded.has(focusedKey)) {
				e.preventDefault();
				expanded.add(focusedKey);
			} else if (e.key === 'ArrowLeft' && isFolder && expanded.has(focusedKey)) {
				e.preventDefault();
				expanded.delete(focusedKey);
			}
		}
	}

	let pending = $derived(loading && !tree);

	// the ancestors of the first visible row are reported to the head, which pins them outside the card
	let crumbs: Crumb[] = [];
	let frame = 0;

	function edge(): number {
		const base = edgeEl?.getBoundingClientRect().bottom ?? 0;
		return base + (crumbs.length ? CRUMB_HEIGHT : 0) + 1;
	}
	function rowFor(key: string): HTMLElement | null {
		return (
			container?.querySelector<HTMLElement>(`[${OUTLINE_ROW_ATTR}="${CSS.escape(key)}"]`) ?? null
		);
	}
	function ancestorsOf(el: HTMLElement): Crumb[] {
		const out: Crumb[] = [];
		let key = el.getAttribute('data-outline-parent') ?? '';
		let guard = 0;
		while (key && guard++ < 32) {
			const row = rowFor(key);
			if (!row) break;
			out.unshift({ key, name: row.getAttribute('data-outline-name') ?? key });
			key = row.getAttribute('data-outline-parent') ?? '';
		}
		return out;
	}
	function updateCrumbs() {
		frame = 0;
		if (!container) return;
		const limit = edge();
		const first = rows().find((el) => el.getBoundingClientRect().bottom > limit);
		const next = first ? ancestorsOf(first) : [];
		if (next.length !== crumbs.length || next.some((c, i) => c.key !== crumbs[i]?.key)) {
			crumbs = next;
			onCrumbs?.(next);
		}
	}
	function onScroll() {
		if (!frame) frame = requestAnimationFrame(updateCrumbs);
	}
	function scrollerFor(): HTMLElement | null {
		let el: HTMLElement | null = container;
		while (el && el.scrollHeight <= el.clientHeight + 1) el = el.parentElement;
		return el;
	}
	export function jumpTo(key: string) {
		const row = rowFor(key);
		const scroller = scrollerFor();
		if (!row || !scroller) return;
		const target = (edgeEl?.getBoundingClientRect().bottom ?? 0) + CRUMB_HEIGHT;
		scroller.scrollTop += row.getBoundingClientRect().top - target;
		focusedKey = key;
	}
	// capture phase, because a scroll event does not bubble and the scrolling ancestor is not known until rows exist
	$effect(() => {
		if (!container) return;
		window.addEventListener('scroll', onScroll, { capture: true, passive: true });
		window.addEventListener('resize', onScroll);
		return () => {
			window.removeEventListener('scroll', onScroll, { capture: true });
			window.removeEventListener('resize', onScroll);
			if (frame) cancelAnimationFrame(frame);
		};
	});
	$effect(() => {
		void expanded.size;
		void tree;
		onScroll();
	});

	// typing a few letters jumps to the next row whose name starts with them, like a file browser
	let typed = '';
	let typedAt = 0;
	const TYPE_AHEAD_MS = 700;
	function typeAhead(char: string) {
		const now = Date.now();
		typed = now - typedAt > TYPE_AHEAD_MS ? char : typed + char;
		typedAt = now;
		const all = rows();
		if (!all.length) return;
		const at = all.findIndex((el) => el.getAttribute(OUTLINE_ROW_ATTR) === focusedKey);
		const order = [...all.slice(at + 1), ...all.slice(0, at + 1)];
		const needle = typed.toLowerCase();
		const hit = order.find((el) =>
			(el.getAttribute('data-outline-name') ?? '').toLowerCase().startsWith(needle)
		);
		if (!hit) return;
		focusedKey = hit.getAttribute(OUTLINE_ROW_ATTR) ?? '';
		hit.scrollIntoView({ block: 'nearest' });
	}
</script>

<svelte:window onkeydown={onKey} />

<div bind:this={container}>
	<ScrollArea orientation="horizontal">
		<ListHeader lead={OUTLINE_LEAD_COLUMNS} {columns} {sortKey} {sortDir} {onSort} />
		<div class="transition-opacity {loading && !pending ? 'opacity-60' : ''}">
			{#if pending}
				<div class="divide-y divide-border/50">
					{#each Array(8) as _, i (i)}
						<div class="flex items-center gap-3 px-4 py-3">
							<Skeleton class="h-5 flex-1" />
							<Skeleton class="hidden h-5 w-16 sm:block" />
							<Skeleton class="hidden h-5 w-40 sm:block" />
						</div>
					{/each}
				</div>
			{:else}
				{#each shownRoots as node (node.key)}
					<OutlineNode {node} depth={0} {ctx} {headless} />
				{/each}
			{/if}
		</div>
	</ScrollArea>

	{#if tree?.truncated}
		<p class="border-b px-4 py-2 text-[11px] text-muted-foreground">
			The tree stops at {tree.total_nodes.toLocaleString()} folders. Narrow the search to see the rest.
		</p>
	{/if}
</div>
