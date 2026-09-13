<script lang="ts">
	import { onDestroy, untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import Search from '@lucide/svelte/icons/search';
	import Share2 from '@lucide/svelte/icons/share-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as Card from '$lib/components/ui/card';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import CorrelationGraph, { type GraphNode } from './correlation-graph.svelte';
	import CorrelationRail from './correlation-rail.svelte';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { mode } from 'mode-watcher';
	import { kindColor } from '$lib/config/correlation';
	import { exactToken } from '$lib/utilities/scan-insights';
	import { LiveRefresh } from '$lib/utilities/live-results';
	import type {
		CorrelationGraph as Graph,
		CorrelationHost,
		CorrelationHub
	} from '$lib/types/correlation';

	interface Props {
		scanId: string;
		projectWide?: boolean;
		projectId: string;
		active?: boolean;
		revision?: number;
		onTab?: (tab: string, filter?: string) => void;
		onTotal?: (total: number) => void;
	}

	let {
		scanId,
		projectId,
		projectWide = false,
		active = true,
		revision = 0,
		onTab,
		onTotal
	}: Props = $props();

	const HEIGHT = 600;
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let graph = $state<Graph | null>(null);
	let loading = $state(false);
	let errored = $state(false);
	let enabled = new SvelteSet<string>();
	let hideCommon = $state(true);
	let hidePlatform = $state(true);
	let crossOnly = $state(false);
	let settled = false;
	let selected = $state<GraphNode | null>(null);
	let search = $state('');
	let chart = $state<ReturnType<typeof CorrelationGraph> | null>(null);
	let seen = $state(false);
	let req = 0;

	$effect(() => {
		if (active) seen = true;
	});

	async function load() {
		if (!projectId || (!scanId && !projectWide)) return;
		const my = ++req;
		loading = true;
		try {
			const res = await subdomainsApi.correlationGraph(projectId, scanId);
			if (my !== req) return;
			graph = res;
			errored = false;
			if (!settled) {
				settled = true;
				for (const k of res.kinds) if (k.default) enabled.add(k.key);
				// a scope over several targets opens on what crosses them
				crossOnly = res.targets_total > 1;
			}
		} catch {
			if (my === req) errored = true;
		} finally {
			if (my === req) loading = false;
		}
	}

	$effect(() => {
		void scanId;
		void projectId;
		if (!seen) return;
		untrack(() => void load());
	});
	const liveRefresh = new LiveRefresh(() => load());
	$effect(() => {
		liveRefresh.notify(revision, active && seen);
	});
	onDestroy(() => liveRefresh.stop());

	let manyTargets = $derived((graph?.targets_total ?? 1) > 1);
	let visible = $derived(
		(h: CorrelationHub) =>
			(!hideCommon || !h.common) && (!hidePlatform || !h.platform) && (!crossOnly || h.targets > 1)
	);
	let hubs = $derived((graph?.hubs ?? []).filter((h) => enabled.has(h.kind) && visible(h)));
	let hosts = $derived(graph?.hosts ?? []);
	let sharing = $derived(new Set(hubs.flatMap((h) => h.members)).size);
	// badge equals the head count
	$effect(() => {
		if (graph) onTotal?.(sharing);
	});
	let hidden = $derived(
		(graph?.hubs ?? []).filter((h) => enabled.has(h.kind) && !visible(h)).length
	);
	// a chip counts what it would draw
	let byKind = $derived.by(() => {
		const shown: Record<string, number> = {};
		const hid: Record<string, number> = {};
		for (const h of graph?.hubs ?? []) {
			const bag = visible(h) ? shown : hid;
			bag[h.kind] = (bag[h.kind] ?? 0) + 1;
		}
		return { shown, hid };
	});
	let kinds = $derived(graph?.kinds ?? []);
	let nothingShared = $derived(!!graph && graph.hubs.length === 0);

	function pickHub(hub: CorrelationHub) {
		const node: GraphNode = {
			id: `hub:${hub.id}`,
			kind: 'hub',
			label: hub.label,
			r: 0,
			hub,
			x: 0,
			y: 0,
			born: 0
		};
		selected = node;
		chart?.focusNode(node.id);
	}
	function pickHost(index: number) {
		const host = hosts[index];
		if (!host) return;
		selected = {
			id: `host:${host.id}`,
			kind: 'host',
			label: host.name,
			r: 0,
			host,
			hostIndex: index,
			x: 0,
			y: 0,
			born: 0
		};
		chart?.focusNode(`host:${host.id}`);
	}
	function openHub(hub: CorrelationHub) {
		onTab?.('web-assets', hub.query);
	}
	function openHost(host: CorrelationHost) {
		onTab?.('web-assets', exactToken('host', host.name));
	}
	function openNode(node: GraphNode) {
		if (node.hub) openHub(node.hub);
		else if (node.host) openHost(node.host);
	}
	function findHost() {
		const needle = search.trim().toLowerCase();
		if (!needle) return;
		const index = hosts.findIndex((h) => h.name.toLowerCase().includes(needle));
		if (index >= 0) pickHost(index);
	}
	function setKinds(values: string[]) {
		enabled.clear();
		for (const v of values) enabled.add(v);
		if (selected?.hub && !enabled.has(selected.hub.kind)) selected = null;
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="flex flex-wrap items-center gap-3 border-b px-4 py-3">
		<div class="flex min-w-0 flex-1 basis-72 flex-col gap-0.5">
			{#if graph}
				<p class="text-sm">
					<b class="font-semibold tabular-nums">{sharing.toLocaleString()}</b> of
					{plural(graph.estate_hosts, 'web asset', 'web assets')} share an identity{crossOnly
						? ' across targets'
						: ''}
					<span class="text-muted-foreground"
						>· {plural(hubs.length, 'shared identity', 'shared identities')}{hidden
							? ` · ${hidden.toLocaleString()} hidden`
							: ''}</span
					>
				</p>
				{#if graph.truncated}
					<p class="text-xs text-muted-foreground">
						{graph.total_hosts.toLocaleString()} of {graph.shared_hosts.toLocaleString()} correlating
						web assets graphed, the ones that answered first.
					</p>
				{:else if manyTargets}
					<p class="text-xs text-muted-foreground">
						Across {graph.targets_total.toLocaleString()} targets.
					</p>
				{/if}
			{:else}
				<Skeleton class="h-5 w-72" />
				<Skeleton class="h-4 w-96" />
			{/if}
		</div>
		<div class="relative w-56">
			<Search
				class="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
			/>
			<Input
				bind:value={search}
				placeholder="Find web asset"
				class="h-8 pl-8 font-mono text-xs"
				aria-label="Find web asset"
				onkeydown={(e) => e.key === 'Enter' && findHost()}
			/>
		</div>
	</div>

	{#if kinds.length}
		<div class="flex flex-wrap items-center gap-2 border-b px-4 py-2">
			<ToggleGroup.Root
				type="multiple"
				size="sm"
				variant="outline"
				class="flex-wrap"
				value={[...enabled]}
				onValueChange={setKinds}
				aria-label="Identity types"
			>
				{#each kinds as k (k.key)}
					<Hint
						text="{k.help}. On {plural(k.hosts, 'web asset', 'web assets')}.{byKind.hid[k.key]
							? ` ${byKind.hid[k.key]} hidden.`
							: ''}"
					>
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<ToggleGroup.Item value={k.key} class="h-7 gap-1.5 px-2 text-xs font-normal">
									<span
										class="size-2 rounded-full"
										style="background:{kindColor(k.key, mode.current === 'dark')}"
									></span>
									{k.label}
									<span class="text-muted-foreground tabular-nums">{byKind.shown[k.key] ?? 0}</span>
								</ToggleGroup.Item>
							</span>
						{/snippet}
					</Hint>
				{/each}
			</ToggleGroup.Root>
			<ToggleGroup.Root
				type="multiple"
				size="sm"
				variant="outline"
				class="ml-auto"
				value={[
					...(hideCommon ? ['common'] : []),
					...(hidePlatform ? ['platform'] : []),
					...(crossOnly ? ['crossing'] : [])
				]}
				onValueChange={(v) => {
					hideCommon = v.includes('common');
					hidePlatform = v.includes('platform');
					crossOnly = v.includes('crossing');
				}}
				aria-label="Hidden identities"
			>
				<Hint text="Identities on half or more of the web assets that carry one">
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<ToggleGroup.Item value="common" class="h-7 px-2 text-xs font-normal"
								>Hide common</ToggleGroup.Item
							>
						</span>
					{/snippet}
				</Hint>
				<Hint
					text="Identities a CDN, platform or certificate authority carries for every tenant, and pages the server wrote"
				>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<ToggleGroup.Item value="platform" class="h-7 px-2 text-xs font-normal"
								>Hide provider</ToggleGroup.Item
							>
						</span>
					{/snippet}
				</Hint>
				{#if manyTargets}
					<Hint text="Identities carried by web assets under more than one target">
						{#snippet child(props)}
							<span {...props} class="inline-flex">
								<ToggleGroup.Item value="crossing" class="h-7 px-2 text-xs font-normal"
									>Crosses targets</ToggleGroup.Item
								>
							</span>
						{/snippet}
					</Hint>
				{/if}
			</ToggleGroup.Root>
		</div>
	{/if}

	{#if errored && !graph}
		<EmptyState
			icon={TriangleAlert}
			title="Graph not loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" class="gap-2" onclick={load}
				><RefreshCw class="size-4" /> Retry</Button
			>
		</EmptyState>
	{:else if loading && !graph}
		<div class="flex items-center justify-center" style="height:{HEIGHT}px">
			<Skeleton class="size-64 rounded-full" />
		</div>
	{:else if nothingShared}
		<EmptyState
			icon={Share2}
			title="No shared identities"
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{:else if graph && hubs.length === 0}
		<EmptyState
			icon={Share2}
			title="No identity types selected"
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{:else if graph}
		<div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_18rem]">
			<CorrelationGraph
				bind:this={chart}
				{hosts}
				{hubs}
				height={HEIGHT}
				selectedId={selected?.id ?? null}
				onSelect={(n) => (selected = n)}
				onOpen={openNode}
				class="border-b lg:border-r lg:border-b-0"
			/>
			<div class="min-h-0" style="height:{HEIGHT}px">
				<CorrelationRail
					{selected}
					{hubs}
					{hosts}
					{kinds}
					onPickHub={pickHub}
					onPickHost={pickHost}
					onOpenHub={openHub}
					onOpenHost={openHost}
					onClear={() => (selected = null)}
				/>
			</div>
		</div>
		<div
			class="flex flex-wrap items-center gap-x-4 gap-y-1 border-t px-4 py-2 text-xs text-muted-foreground"
		>
			<span>Filled dot: 2xx response. Hollow dot: no 2xx response.</span>
			<span>Hub size: number of web assets. Dashed ring: TLS or certificate identity.</span>
		</div>
	{/if}
</Card.Root>
