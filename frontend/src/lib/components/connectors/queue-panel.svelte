<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import SearchIcon from '@lucide/svelte/icons/search';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import LockIcon from '@lucide/svelte/icons/lock';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import ListTreeIcon from '@lucide/svelte/icons/list-tree';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area/index.js';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import SelectionActionBar from '$lib/components/selection-action-bar.svelte';
	import { writeClipboard } from '$lib/utilities/clipboard';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import ProxySend from '$lib/components/scans/results/endpoints/proxy-send.svelte';
	import {
		handoffToProxy,
		previewHandoff,
		proxyName
	} from '$lib/components/scans/results/endpoints/proxy';
	import RequestDialog from './request-dialog.svelte';
	import { proxyTool } from '$lib/stores/proxy-tool.svelte';
	import SendIcon from '@lucide/svelte/icons/send';
	import {
		ACTION_KIND_LABELS,
		CONNECTOR_POLL_MS,
		LIVE_POLL_MS,
		NEW_ROW_MS,
		MAX_HANDOFF,
		type ActionKind,
		CANDIDATE_STATES,
		CANDIDATE_STATE_LABELS,
		NOTICE_HELP,
		NOTICE_LABELS,
		SOURCE_TOOL_LABELS,
		noticeTone
	} from '$lib/config/connectors';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import { afterPause } from '$lib/utilities/debounce';
	import { httpStatusTextClass } from '$lib/utilities/scan-correlation';
	import { plural, pluralWord } from '$lib/utilities/strings';
	import { externalHref } from '$lib/utilities/links';
	import type { Candidate, CandidateQuery, Connector, QueueView } from '$lib/types/connector';

	let {
		connector,
		projectId,
		view,
		live = false
	}: {
		connector: Connector;
		projectId: string;
		view: QueueView;
		live?: boolean;
	} = $props();

	const VIEW_QUERY: Record<QueueView, CandidateQuery> = {
		missed: { notice: 'unseen_by_scans' },
		flagged: { flagged: true },
		out_of_scope: { notice: 'out_of_scope' },
		all: {}
	};
	const VIEW_EMPTY: Record<QueueView, string> = {
		missed: 'No missed requests',
		flagged: 'No flagged requests',
		out_of_scope: 'No out-of-scope requests',
		all: 'No requests'
	};

	const HEAD =
		'px-4 py-2 text-left text-2xs font-medium tracking-wide text-muted-foreground uppercase whitespace-nowrap';
	const PAGE_SIZE = 50;
	const PARAMS_SHOWN = 3;

	let stateFilter = $state<string>('');
	let host = $state<string>('');
	let search = $state('');
	let applied = $state('');
	let confirming = $state<{ action: 'scan' | 'ignore'; ids: string[] } | null>(null);
	let openedId = $state<string | null>(null);
	let now = $state(Date.now());
	let pageNumber = $state(0);
	let picked = new SvelteSet<string>();
	const sending = new SvelteSet<string>();
	let scanning = $state(false);
	let acting = $state(false);

	const connectorId = $derived(connector.id);
	const page = $derived(connectors.queue);
	const rows = $derived(page?.rows ?? []);
	const hosts = $derived(page?.hosts ?? []);
	const filters = $derived<CandidateQuery>({
		...VIEW_QUERY[view],
		state: stateFilter || undefined,
		host: host || undefined,
		search: applied || undefined,
		page: pageNumber + 1
	});
	const count = $derived(confirming?.ids.length ?? 0);
	const noun = $derived(pluralWord(count, 'request'));
	const openedRow = $derived(rows.find((r) => r.id === openedId) ?? null);
	const sendLabel = $derived(
		`Send to ${proxyName(connector, connectors.catalog)} ${ACTION_KIND_LABELS[proxyTool.kind]}`
	);

	$effect(() => {
		void view;
		untrack(() => (pageNumber = 0));
	});

	$effect(() => {
		const next = search;
		return afterPause(() => {
			if (applied === next) return;
			applied = next;
			pageNumber = 0;
		});
	});

	$effect(() => {
		const id = connectorId;
		const query = filters;
		untrack(() => {
			picked.clear();
			void connectors.loadQueue(id, projectId, query);
		});
	});

	$effect(() => {
		const id = connectorId;
		const query = filters;
		const every = live ? LIVE_POLL_MS : CONNECTOR_POLL_MS;
		const timer = setInterval(() => {
			now = Date.now();
			if (document.hidden || picked.size) return;
			void connectors.loadQueue(id, projectId, query, true);
		}, every);
		return () => clearInterval(timer);
	});

	function toggle(id: string) {
		if (picked.has(id)) picked.delete(id);
		else picked.add(id);
	}

	function toggleAll() {
		const all = picked.size === rows.length;
		picked.clear();
		if (!all) for (const row of rows) picked.add(row.id);
	}

	async function reload() {
		await connectors.loadQueue(connector.id, projectId, filters);
		await connectors.load(projectId, true);
	}

	async function scan(ids: string[]) {
		scanning = true;
		try {
			const runs = await connectorsApi.scan(connector.id, projectId, ids);
			confirming = null;
			openedId = null;
			picked.clear();
			await reload();
			if (runs.length === 1) void goto(ROUTES.scan(runs[0].id));
			else toast.success(`${runs.length} scans started`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Scan not started');
		} finally {
			scanning = false;
		}
	}

	async function sendToProxy(_connectorId: string, kind: ActionKind) {
		const sent = await handoffToProxy({
			connectorId: connector.id,
			projectId,
			body: { kind, candidate_ids: [...picked].slice(0, MAX_HANDOFF) },
			connectors: [connector],
			catalog: connectors.catalog
		});
		if (sent) {
			picked.clear();
			await reload();
		}
		return sent;
	}

	async function copyPicked() {
		const urls = rows.filter((row) => picked.has(row.id)).map((row) => row.url);
		if (!urls.length) return;
		if (await writeClipboard(urls.join('\n')))
			toast.success(`${urls.length.toLocaleString()} URLs copied`);
		else toast.error('Clipboard not available');
	}

	async function sendOne(row: Candidate, kind: ActionKind, request?: string) {
		return handoffToProxy({
			connectorId: connector.id,
			projectId,
			body: { kind, candidate_ids: [row.id], request },
			connectors: [connector],
			catalog: connectors.catalog
		});
	}

	async function sendRow(row: Candidate) {
		if (sending.has(row.id)) return;
		sending.add(row.id);
		try {
			await sendOne(row, proxyTool.kind);
		} finally {
			sending.delete(row.id);
		}
	}

	function previewOne(row: Candidate) {
		return previewHandoff({
			connectorId: connector.id,
			projectId,
			body: { candidate_ids: [row.id] }
		});
	}

	function fresh(row: Candidate): boolean {
		return now - new Date(row.first_seen_at).getTime() < NEW_ROW_MS;
	}

	async function ignore(ids: string[]) {
		acting = true;
		try {
			await connectorsApi.setState(connector.id, projectId, ids, 'ignored');
			confirming = null;
			openedId = null;
			picked.clear();
			await reload();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Requests not ignored');
		} finally {
			acting = false;
		}
	}

	function endpointsLink(row: Candidate): string {
		const dir = row.path.slice(0, row.path.lastIndexOf('/') + 1) || '/';
		return ROUTES.surface('endpoints', { ep_host: row.host, ep_dir: dir });
	}
</script>

<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
	<div class="relative min-w-52 flex-1">
		<SearchIcon
			class="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2"
		/>
		<Input bind:value={search} placeholder="Filter by URL" class="h-8 pl-8 text-xs" />
	</div>
	{#if hosts.length > 1}
		<Select.Root
			type="single"
			value={host}
			onValueChange={(v) => {
				host = v ?? '';
				pageNumber = 0;
			}}
		>
			<Select.Trigger class="h-8 w-64 text-xs">
				{host || `All hosts · ${hosts.length}`}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="">All hosts</Select.Item>
				{#each hosts as row (row.host)}
					<Select.Item value={row.host}>{row.host} · {row.count}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
	{/if}
	<Select.Root
		type="single"
		value={stateFilter}
		onValueChange={(v) => {
			stateFilter = v ?? '';
			pageNumber = 0;
		}}
	>
		<Select.Trigger class="h-8 w-36 text-xs">
			{stateFilter ? CANDIDATE_STATE_LABELS[stateFilter as Candidate['state']] : 'Any state'}
		</Select.Trigger>
		<Select.Content>
			<Select.Item value="">Any state</Select.Item>
			{#each CANDIDATE_STATES as s (s)}
				<Select.Item value={s}>{CANDIDATE_STATE_LABELS[s]}</Select.Item>
			{/each}
		</Select.Content>
	</Select.Root>
	<span class="text-muted-foreground text-xs tabular-nums">
		{plural(page?.total ?? 0, 'request')}
	</span>
	{#if live}
		<span class="flex items-center gap-1.5 text-xs">
			<span class="bg-success size-1.5 rounded-full" aria-hidden="true"></span>
			Live
		</span>
	{/if}
</div>

{#if connector.unassigned > 0 && connector.unassigned === connector.candidates}
	<p class="text-muted-foreground border-b px-4 py-2 text-xs">No target covers these requests.</p>
{/if}

{#if connectors.queueLoading && rows.length === 0}
	<div class="space-y-2 p-4">
		{#each Array(6) as _, i (i)}
			<Skeleton class="h-11 w-full" />
		{/each}
	</div>
{:else if connectors.queueError && rows.length === 0}
	<EmptyState
		icon={TriangleAlertIcon}
		title="Requests not loaded"
		description={connectors.queueError}
		class="rounded-none border-0 bg-transparent py-16"
	>
		<Button
			variant="outline"
			size="sm"
			onclick={() => connectors.loadQueue(connector.id, projectId, filters)}
		>
			Retry
		</Button>
	</EmptyState>
{:else if rows.length === 0}
	<EmptyState
		icon={RadarIcon}
		title={VIEW_EMPTY[view]}
		class="rounded-none border-0 bg-transparent py-16"
	/>
{:else}
	<ScrollArea orientation="horizontal">
		<table class="w-full min-w-[760px] table-fixed text-sm">
			<thead>
				<tr class="border-b bg-muted/20">
					<th class="w-10 px-3 py-2">
						<Checkbox
							checked={picked.size === rows.length && rows.length > 0}
							onCheckedChange={toggleAll}
							aria-label="Select all"
						/>
					</th>
					<th class="{HEAD} w-16">Method</th>
					<th class={HEAD}>Shape</th>
					<th class="{HEAD} w-32">Parameters</th>
					<th class="{HEAD} w-16 text-right">Status</th>
					<th class="{HEAD} w-12 text-right">Hits</th>
					<th class="{HEAD} w-20">Source</th>
					<th class="{HEAD} w-20 text-right">Seen</th>
					<th class="w-24 px-2 py-2"></th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row (row.id)}
					<tr class="border-b last:border-b-0">
						<td class="px-3 py-2.5 align-top">
							<span class="flex h-5 items-center">
								<Checkbox
									checked={picked.has(row.id)}
									onCheckedChange={() => toggle(row.id)}
									aria-label={row.url}
								/>
							</span>
						</td>
						<td
							class="text-muted-foreground px-4 py-2.5 align-top font-mono text-2xs leading-5 whitespace-nowrap"
						>
							{row.methods.join(' ') || 'GET'}
						</td>
						<td class="px-4 py-2.5 align-top">
							<div class="flex min-w-0 items-center gap-1.5">
								{#if row.authenticated}
									<Hint text="Session present">
										{#snippet child(props)}
											<span {...props} class="flex h-5 shrink-0 items-center">
												<LockIcon class="text-muted-foreground size-3" />
											</span>
										{/snippet}
									</Hint>
								{/if}
								<button
									type="button"
									class="hover:text-primary min-w-0 truncate text-left font-mono text-xs leading-5 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
									onclick={() => (openedId = row.id)}
								>
									{row.path}
								</button>
								{#if fresh(row)}
									<span class="text-info shrink-0 text-2xs font-medium">New</span>
								{/if}
							</div>
							{#if row.notices.length > 0 || row.title || (!host && hosts.length > 1)}
								<div class="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-2">
									{#if !host && hosts.length > 1}
										<span class="text-muted-foreground min-w-0 truncate font-mono text-2xs"
											>{row.host}</span
										>
									{/if}
									{#each row.notices as item (item)}
										<Hint text={NOTICE_HELP[item] ?? ''}>
											{#snippet child(props)}
												<span {...props} class="text-2xs whitespace-nowrap {noticeTone(item)}">
													{NOTICE_LABELS[item] ?? item}
												</span>
											{/snippet}
										</Hint>
									{/each}
									{#if row.title}
										<span class="text-muted-foreground/70 min-w-0 truncate text-2xs"
											>{row.title}</span
										>
									{/if}
								</div>
							{/if}
						</td>
						<td class="px-4 py-2.5 align-top">
							{#if row.param_count > 0}
								<Hint text={row.params.join(', ')}>
									{#snippet child(props)}
										<span {...props} class="block truncate font-mono text-2xs leading-5">
											{row.params.slice(0, PARAMS_SHOWN).join(' ')}{row.param_count > PARAMS_SHOWN
												? ` +${row.param_count - PARAMS_SHOWN}`
												: ''}
										</span>
									{/snippet}
								</Hint>
							{:else}
								<span class="text-muted-foreground/40 text-2xs leading-5">—</span>
							{/if}
						</td>
						<td
							class="px-4 py-2.5 text-right align-top font-mono text-xs leading-5 tabular-nums {httpStatusTextClass(
								row.status_code
							)}">{row.status_code ?? '—'}</td
						>
						<td
							class="text-muted-foreground px-4 py-2.5 text-right align-top text-2xs leading-5 tabular-nums"
							>{row.hits > 1 ? row.hits : ''}</td
						>
						<td class="text-muted-foreground px-4 py-2.5 align-top text-2xs leading-5"
							>{SOURCE_TOOL_LABELS[row.source_tool] ?? row.source_tool}</td
						>
						<td
							class="text-muted-foreground px-4 py-2.5 text-right align-top text-2xs leading-5 whitespace-nowrap"
							>{relativeTime(row.last_seen_at)}</td
						>
						<td class="px-2 py-1.5 align-top">
							<span class="flex h-7 items-center justify-end gap-0.5">
								{#if !connector.paused}
									<Hint text={sendLabel}>
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-7"
												aria-label={sendLabel}
												disabled={sending.has(row.id)}
												onclick={() => sendRow(row)}
											>
												<SendIcon class="size-3.5" />
											</Button>
										{/snippet}
									</Hint>
								{/if}
								{#if row.target_id}
									<Hint text="Open in Endpoints">
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-7"
												aria-label="Open in Endpoints"
												href={endpointsLink(row)}
											>
												<ListTreeIcon class="size-3.5" />
											</Button>
										{/snippet}
									</Hint>
								{/if}
								<Hint text="Open in a new tab">
									{#snippet child(props)}
										<Button
											{...props}
											variant="ghost"
											size="icon"
											class="size-7"
											aria-label="Open in a new tab"
											href={externalHref(row.url)}
											target="_blank"
											rel="noopener noreferrer"
										>
											<ExternalLinkIcon class="size-3.5" />
										</Button>
									{/snippet}
								</Hint>
							</span>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</ScrollArea>
	<ResultsPagination
		total={page?.total ?? 0}
		page={pageNumber}
		pageSize={PAGE_SIZE}
		noun="request"
		onPage={(next) => (pageNumber = next)}
	/>
{/if}

<SelectionActionBar selectedCount={picked.size} noun="request" onClear={() => picked.clear()}>
	<LoadingButton
		loading={scanning}
		variant="ghost"
		size="sm"
		class="font-medium"
		loadingLabel="Starting"
		onclick={() => (confirming = { action: 'scan', ids: [...picked] })}
	>
		<RadarIcon class="h-3.5 w-3.5 text-muted-foreground" />
		Scan {picked.size}
	</LoadingButton>
	{#if !connector.paused}
		<ProxySend
			connectors={[connector]}
			catalog={connectors.catalog}
			variant="ghost"
			onSend={sendToProxy}
		/>
	{/if}
	<Button variant="ghost" size="sm" class="font-medium" onclick={copyPicked}>
		<CopyIcon class="h-3.5 w-3.5 text-muted-foreground" />
		Copy URLs
	</Button>
	<Button
		variant="ghost"
		size="sm"
		class="font-medium"
		disabled={acting}
		onclick={() => (confirming = { action: 'ignore', ids: [...picked] })}
	>
		<EyeOffIcon class="h-3.5 w-3.5 text-muted-foreground" />
		Ignore
	</Button>
</SelectionActionBar>

<RequestDialog
	row={openedRow}
	{connector}
	onClose={() => (openedId = null)}
	onSend={(kind, request) => (openedRow ? sendOne(openedRow, kind, request) : null)}
	onPreview={() => (openedRow ? previewOne(openedRow) : Promise.resolve(null))}
	onScan={(row) => (confirming = { action: 'scan', ids: [row.id] })}
	onIgnore={(row) => (confirming = { action: 'ignore', ids: [row.id] })}
	endpointsHref={openedRow?.target_id ? endpointsLink(openedRow) : null}
/>

<ConfirmDialog
	open={confirming !== null}
	title={confirming?.action === 'scan' ? `Scan ${count} ${noun}` : `Ignore ${count} ${noun}`}
	description={confirming?.action === 'scan' ? 'One scan per target.' : undefined}
	confirmLabel={confirming?.action === 'scan' ? 'Start scan' : 'Ignore'}
	loadingLabel={confirming?.action === 'scan' ? 'Starting' : 'Ignoring'}
	loading={scanning || acting}
	onOpenChange={(v) => {
		if (!v) confirming = null;
	}}
	onConfirm={() => {
		if (!confirming) return;
		if (confirming.action === 'scan') void scan(confirming.ids);
		else void ignore(confirming.ids);
	}}
/>
