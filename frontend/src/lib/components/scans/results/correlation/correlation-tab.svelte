<script lang="ts">
	import { SURFACE, SurfaceDimension, type ResultTab } from '$lib/config/surface';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import Search from '@lucide/svelte/icons/search';
	import Share2 from '@lucide/svelte/icons/share-2';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Button } from '$lib/components/ui/button';
	import * as InputGroup from '$lib/components/ui/input-group';
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
	import { plural } from '$lib/utilities/strings';
	import type {
		CorrelationGraph as Graph,
		CorrelationHost,
		CorrelationHub
	} from '$lib/types/correlation';

	interface Props {
		scanId: string;
		projectId: string;
		active?: boolean;
		revision?: number;
		onTab?: (tab: ResultTab, filter?: string) => void;
		onTotal?: (total: number) => void;
	}

	let { scanId, projectId, active = true, revision = 0, onTab, onTotal }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];

	const HEIGHT = 600;

	let graph = $state<Graph | null>(null);
	let loading = $state(false);
	let errored = $state(false);
	let enabled = new SvelteSet<string>();
	let hideCommon = $state(true);
	let hidePlatform = $state(true);
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
		if (!projectId || !scanId) return;
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

	let visible = $derived(
		(h: CorrelationHub) => (!hideCommon || !h.common) && (!hidePlatform || !h.platform)
	);
	let hubs = $derived((graph?.hubs ?? []).filter((h) => enabled.has(h.kind) && visible(h)));
	let hosts = $derived(graph?.hosts ?? []);
	let sharing = $derived(new Set(hubs.flatMap((h) => h.members)).size);
	$effect(() => {
		if (graph) onTotal?.(sharing);
	});
	let hidden = $derived(
		(graph?.hubs ?? []).filter((h) => enabled.has(h.kind) && !visible(h)).length
	);
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
		onTab?.(WEB.tab, hub.query);
	}
	function openHost(host: CorrelationHost) {
		onTab?.(WEB.tab, exactToken('host', host.name));
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
	function showAll() {
		hideCommon = false;
		hidePlatform = false;
		setKinds(kinds.map((k) => k.key));
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<div class="flex flex-wrap items-center gap-3 border-b px-4 py-3">
		<div class="flex min-w-0 flex-1 basis-72 flex-col gap-0.5">
			{#if graph}
				<p class="text-sm">
					<b class="font-semibold tabular-nums">{sharing.toLocaleString()}</b> of
					{plural(graph.estate_hosts, 'web asset', 'web assets')} share an identity
					<span class="text-muted-foreground"
						>· {plural(hubs.length, 'shared identity', 'shared identities')}{hidden
							? ` · ${hidden.toLocaleString()} hidden`
							: ''}</span
					>
				</p>
				{#if graph.truncated}
					<p class="text-xs text-muted-foreground">
						{graph.total_hosts.toLocaleString()} of {graph.shared_hosts.toLocaleString()} correlating
						web assets graphed.
					</p>
				{/if}
			{:else}
				<Skeleton class="h-5 w-72" />
				<Skeleton class="h-4 w-96" />
			{/if}
		</div>
		<InputGroup.Root class="w-56">
			<InputGroup.Addon><Search /></InputGroup.Addon>
			<InputGroup.Input
				bind:value={search}
				placeholder="Find web asset"
				class="font-mono text-xs"
				aria-label="Find web asset"
				onkeydown={(e) => e.key === 'Enter' && findHost()}
			/>
		</InputGroup.Root>
	</div>

	{#if kinds.length}
		<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
			<ToggleGroup.Root
				type="multiple"
				variant="outline"
				spacing={1}
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
							<ToggleGroup.Item {...props} value={k.key} class="h-9 gap-1.5 px-3 font-normal">
								<span
									class="size-2 rounded-full"
									style="background:{kindColor(k.key, mode.current === 'dark')}"
									aria-hidden="true"
								></span>
								{k.label}
								<span class="text-muted-foreground tabular-nums">{byKind.shown[k.key] ?? 0}</span>
							</ToggleGroup.Item>
						{/snippet}
					</Hint>
				{/each}
			</ToggleGroup.Root>
			<ToggleGroup.Root
				type="multiple"
				variant="outline"
				spacing={1}
				class="ml-auto"
				value={[...(hideCommon ? ['common'] : []), ...(hidePlatform ? ['platform'] : [])]}
				onValueChange={(v) => {
					hideCommon = v.includes('common');
					hidePlatform = v.includes('platform');
				}}
				aria-label="Hidden identities"
			>
				<Hint text="Identities on half or more of the web assets that carry one">
					{#snippet child(props)}
						<ToggleGroup.Item {...props} value="common" class="h-9 px-3 font-normal"
							>Hide common</ToggleGroup.Item
						>
					{/snippet}
				</Hint>
				<Hint
					text="Identities a CDN, platform or certificate authority carries for every tenant, and pages the server wrote"
				>
					{#snippet child(props)}
						<ToggleGroup.Item {...props} value="platform" class="h-9 px-3 font-normal"
							>Hide provider</ToggleGroup.Item
						>
					{/snippet}
				</Hint>
			</ToggleGroup.Root>
		</div>
	{/if}

	{#if errored && !graph}
		<EmptyState
			icon={TriangleAlert}
			title="Graph not loaded"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" size="sm" onclick={() => load()}>Retry</Button>
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
	{:else if graph && enabled.size === 0}
		<EmptyState
			icon={Share2}
			title="No identity types selected"
			class="rounded-none border-0 bg-transparent py-16"
		/>
	{:else if graph && hubs.length === 0}
		<EmptyState
			icon={Share2}
			title="Shared identities hidden"
			class="rounded-none border-0 bg-transparent py-16"
		>
			<Button variant="outline" size="sm" onclick={showAll}>Show all identities</Button>
		</EmptyState>
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
