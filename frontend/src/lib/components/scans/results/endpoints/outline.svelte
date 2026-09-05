<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';

	import { Skeleton } from '$lib/components/ui/skeleton';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import ListHeader from '../table/list-header.svelte';
	import ResultsPagination from '../table/results-pagination.svelte';
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
	import { writeClipboard } from '$lib/utilities/clipboard';
	import type {
		EndpointFilter,
		EndpointRead,
		EndpointTree,
		HostPage,
		MergedLeaf,
		TreeNode
	} from '$lib/utilities/endpoints';

	interface Props {
		projectId: string;
		scanId: string;
		tree?: EndpointTree | null;
		hosts?: HostPage | null;
		loading?: boolean;
		merged?: boolean;
		filter: EndpointFilter;
		terms?: string[];
		columns: TableColumn[];
		pad?: string;
		active?: boolean;
		paused?: boolean;
		embedded?: boolean;
		searching?: boolean;
		selectedId?: string | null;
		sortKey: string;
		sortDir: 1 | -1;
		onSort: (key: string) => void;
		onOpen: (e: EndpointRead) => void;
		onFilter: (token: string) => void;
		onShowInList?: (token: string) => void;
		onHost: (host: string) => void;
		onHostPage?: (page: number) => void;
		onExpandedChange?: (count: number) => void;
		onVerify?: (node: TreeNode) => void;
		edgeEl?: HTMLElement | null;
		onCrumbs?: (crumbs: Crumb[]) => void;
	}

	let {
		projectId,
		scanId,
		tree = null,
		hosts = null,
		loading = false,
		merged = false,
		filter,
		terms = [],
		columns,
		pad = 'py-3',
		active = true,
		paused = false,
		embedded = false,
		searching = false,
		selectedId = null,
		sortKey,
		sortDir,
		onSort,
		onOpen,
		onFilter,
		onShowInList,
		onHost,
		onHostPage,
		onExpandedChange,
		onVerify,
		edgeEl = null,
		onCrumbs
	}: Props = $props();

	const COPY_CAP = 5000;
	const COPY_PAGE = 200;
	const REMEMBER_CAP = 400;

	const expanded = new SvelteSet<string>();
	let budget = $state<OpenBudget>({ enabled: false, used: 0, decided: new SvelteSet<string>() });
	let autoKey = '';
	let focusedKey = $state('');
	let container = $state<HTMLElement | null>(null);

	let roots = $derived(hosts ? hosts.items : (tree?.nodes ?? []));
	// merged and embedded trees have one synthetic root whose children are the real top level
	let headless = $derived(merged || embedded);
	let shownRoots = $derived(headless ? roots.slice(0, 1) : roots);
	let rememberKey = $derived(
		embedded ? '' : `${STORAGE_KEYS.endpointsExpanded}:${scanId}:${merged ? 'merged' : 'host'}`
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
		if ((!tree && !hosts) || key === autoKey) return;
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
	});

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

	async function copyBranch(node: TreeNode) {
		const base: EndpointFilter = {
			...filter,
			host: merged ? null : node.host,
			dir_path: node.kind === 'host' ? null : node.path,
			subtree: true,
			sort: 'path',
			direction: 'asc',
			size: COPY_PAGE,
			page: 1
		};
		const urls: string[] = [];
		try {
			for (let page = 1; urls.length < COPY_CAP; page++) {
				const res = await endpointsApi.search(projectId, scanId, { ...base, page });
				urls.push(...res.items.map((e) => e.url));
				if (res.items.length < COPY_PAGE || urls.length >= res.total) break;
			}
			const unique = [...new Set(urls)].slice(0, COPY_CAP);
			await writeClipboard(unique.join('\n'));
			toast.success(
				`Copied ${unique.length.toLocaleString()} ${unique.length === 1 ? 'URL' : 'URLs'}${
					urls.length >= COPY_CAP ? ' (first 5,000)' : ''
				}`
			);
		} catch {
			toast.error('The URLs could not be copied.');
		}
	}

	async function collectUrls(node: TreeNode): Promise<{ urls: string[]; capped: boolean }> {
		const base: EndpointFilter = {
			...filter,
			host: merged ? null : node.host,
			dir_path: node.kind === 'host' ? null : node.path,
			subtree: true,
			sort: 'path',
			direction: 'asc',
			size: COPY_PAGE,
			page: 1
		};
		const urls: string[] = [];
		for (let page = 1; urls.length < COPY_CAP; page++) {
			const res = await endpointsApi.search(projectId, scanId, { ...base, page });
			urls.push(...res.items.map((e) => e.url));
			if (res.items.length < COPY_PAGE || urls.length >= res.total) break;
		}
		return { urls: [...new Set(urls)].slice(0, COPY_CAP), capped: urls.length >= COPY_CAP };
	}

	// paths relative to the folder, one per line: what ffuf wants when you point it at a sibling host
	async function copyWordlist(node: TreeNode) {
		try {
			const { urls, capped } = await collectUrls(node);
			const prefix = node.kind === 'host' || node.kind === 'group' ? '/' : node.path;
			const words = new SvelteSet<string>();
			for (const raw of urls) {
				try {
					const path = new URL(raw).pathname;
					const rel = path.startsWith(prefix) ? path.slice(prefix.length) : path.replace(/^\//, '');
					if (rel) words.add(rel);
				} catch {
					// an unparsable url has no path to offer
				}
			}
			await writeClipboard([...words].sort().join('\n'));
			toast.success(
				`Copied ${words.size.toLocaleString()} ${words.size === 1 ? 'path' : 'paths'}${capped ? ' (first 5,000 URLs)' : ''}`
			);
		} catch {
			toast.error('The paths could not be copied.');
		}
	}

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
		toggle,
		openEndpoint: onOpen,
		openById,
		openMerged,
		onFilter,
		onShowInList: onShowInList ?? onFilter,
		onHost,
		copyBranch,
		copyWordlist,
		verifyBranch: onVerify
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

	let pending = $derived(loading && !tree && !hosts);

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
		void hosts;
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

	{#if hosts && hosts.total > hosts.size && onHostPage}
		<ResultsPagination
			total={hosts.total}
			page={hosts.page - 1}
			pageSize={hosts.size}
			noun="host"
			plural="hosts"
			onPage={(p) => onHostPage(p + 1)}
		/>
	{/if}
</div>
