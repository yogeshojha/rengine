<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import SearchIcon from '@lucide/svelte/icons/search';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import SendIcon from '@lucide/svelte/icons/send';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import LockIcon from '@lucide/svelte/icons/lock';
	import ExternalLinkIcon from '@lucide/svelte/icons/external-link';
	import ListTreeIcon from '@lucide/svelte/icons/list-tree';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Select from '$lib/components/ui/select/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import PanelHead from '$lib/components/panel-head.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import CodeBlock from '$lib/components/code-block.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import {
		CANDIDATE_STATES,
		CANDIDATE_STATE_LABELS,
		NOTICE_HELP,
		NOTICE_LABELS,
		SOURCE_TOOL_LABELS,
		noticeTone
	} from '$lib/config/connectors';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import type { Candidate, CandidateQuery, Connector } from '$lib/types/connector';

	let {
		connector,
		projectId,
		preset = null,
		onPresetApplied
	}: {
		connector: Connector;
		projectId: string;
		preset?: CandidateQuery | null;
		onPresetApplied?: () => void;
	} = $props();

	const HEAD =
		'px-4 py-2 text-left text-2xs font-semibold tracking-wider text-muted-foreground uppercase whitespace-nowrap';
	const PAGE_SIZE = 50;
	const PARAMS_SHOWN = 3;

	let stateFilter = $state<string>('new');
	let host = $state<string>('');
	let notice = $state<string>('');
	let known = $state<'any' | 'yes' | 'no'>('any');
	let search = $state('');
	let pageNumber = $state(1);
	let picked = new SvelteSet<string>();
	let opened = new SvelteSet<string>();
	let scanning = $state(false);
	let sending = $state(false);
	let acting = $state(false);
	let error = $state<string | null>(null);

	const page = $derived(connectors.queue);
	const rows = $derived(page?.rows ?? []);
	const hosts = $derived(page?.hosts ?? []);
	const filters = $derived<CandidateQuery>({
		state: stateFilter || undefined,
		host: host || undefined,
		notice: notice || undefined,
		known: known === 'any' ? undefined : known === 'yes',
		search: search || undefined,
		page: pageNumber
	});

	$effect(() => {
		if (!preset) return;
		untrack(() => {
			stateFilter = preset.state ?? '';
			host = preset.host ?? '';
			notice = preset.notice ?? '';
			known = preset.known === undefined ? 'any' : preset.known ? 'yes' : 'no';
			search = preset.search ?? '';
			onPresetApplied?.();
		});
	});

	$effect(() => {
		const id = connector.id;
		const query = filters;
		untrack(() => {
			picked.clear();
			void connectors.loadQueue(id, projectId, query);
		});
	});

	$effect(() => {
		void stateFilter;
		void host;
		void notice;
		void known;
		void search;
		untrack(() => (pageNumber = 1));
	});

	$effect(() => {
		if (typeof document === 'undefined') return;
		const id = connector.id;
		const query = filters;
		const timer = setInterval(() => {
			if (document.hidden || picked.size) return;
			void connectors.loadQueue(id, projectId, query);
		}, 10_000);
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

	function toggleSample(id: string) {
		if (opened.has(id)) opened.delete(id);
		else opened.add(id);
	}

	async function reload() {
		await connectors.loadQueue(connector.id, projectId, filters);
		await connectors.load(projectId, true);
	}

	async function scan() {
		scanning = true;
		error = null;
		try {
			const runs = await connectorsApi.scan(connector.id, projectId, [...picked]);
			picked.clear();
			await reload();
			if (runs.length === 1) void goto(ROUTES.scan(runs[0].id));
			else toast.success(`${runs.length} scans started.`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Scan not started.';
		} finally {
			scanning = false;
		}
	}

	async function sendToProxy() {
		sending = true;
		error = null;
		try {
			const result = await connectorsApi.send(connector.id, projectId, [...picked]);
			picked.clear();
			await reload();
			toast.success(`${result.queued} sent to Repeater.`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Requests not queued.';
		} finally {
			sending = false;
		}
	}

	async function ignore() {
		acting = true;
		try {
			await connectorsApi.setState(connector.id, projectId, [...picked], 'ignored');
			picked.clear();
			await reload();
		} finally {
			acting = false;
		}
	}

	function statusTone(code: number | null): string {
		if (code === null) return 'text-muted-foreground';
		if (code >= 500) return 'text-destructive';
		if (code >= 400) return 'text-warning';
		return 'text-success';
	}

	function endpointsLink(row: Candidate): string {
		const dir = row.path.slice(0, row.path.lastIndexOf('/') + 1) || '/';
		return ROUTES.surface('endpoints', { ep_host: row.host, ep_dir: dir });
	}
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title="Queue" description="Request shapes recorded through this connector">
		<span class="tabular-nums">{page?.total ?? 0} shown</span>
	</PanelHead>

	<div class="flex flex-wrap items-end justify-between gap-x-4 border-b px-2">
		<CountTabs
			tabs={[
				{ key: 'all', label: 'All' },
				...CANDIDATE_STATES.map((s) => ({ key: s, label: CANDIDATE_STATE_LABELS[s] }))
			]}
			value={stateFilter || 'all'}
			counts={{
				all: Object.values(page?.counts ?? {}).reduce((a, b) => a + b, 0),
				...(page?.counts ?? {})
			}}
			onChange={(key) => (stateFilter = key === 'all' ? '' : key)}
		/>
	</div>

	<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
		<div class="relative min-w-52 flex-1">
			<SearchIcon
				class="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2"
			/>
			<Input bind:value={search} placeholder="Filter by URL" class="h-8 pl-8 text-xs" />
		</div>
		<Select.Root
			type="single"
			value={known}
			onValueChange={(v) => (known = (v as typeof known) || 'any')}
		>
			<Select.Trigger class="h-8 w-44 text-xs">
				{known === 'any'
					? 'All shapes'
					: known === 'yes'
						? 'Found by a scan'
						: 'Not found by scans'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="any">All shapes</Select.Item>
				<Select.Item value="yes">Found by a scan</Select.Item>
				<Select.Item value="no">Not found by scans</Select.Item>
			</Select.Content>
		</Select.Root>
		<Select.Root type="single" value={notice} onValueChange={(v) => (notice = v ?? '')}>
			<Select.Trigger class="h-8 w-52 text-xs">
				{notice ? NOTICE_LABELS[notice] : 'Any notice'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="">Any notice</Select.Item>
				{#each Object.entries(NOTICE_LABELS) as [key, label] (key)}
					<Select.Item value={key}>{label}</Select.Item>
				{/each}
			</Select.Content>
		</Select.Root>
		{#if hosts.length > 1}
			<Select.Root type="single" value={host} onValueChange={(v) => (host = v ?? '')}>
				<Select.Trigger class="h-8 w-64 text-xs">
					{host || `All hosts (${hosts.length})`}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="">All hosts</Select.Item>
					{#each hosts as row (row.host)}
						<Select.Item value={row.host}>{row.host} · {row.count}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		{/if}
	</div>

	{#if picked.size > 0}
		<div class="bg-muted/40 flex flex-wrap items-center gap-3 border-b px-4 py-2.5">
			<span class="text-sm font-medium tabular-nums">{picked.size} selected</span>
			<div class="ml-auto flex items-center gap-2">
				<Button variant="ghost" size="sm" disabled={acting} onclick={() => ignore()}>
					<EyeOffIcon class="size-3.5" />
					Ignore
				</Button>
				<LoadingButton
					loading={sending}
					variant="outline"
					size="sm"
					onclick={sendToProxy}
					disabled={connector.paused}
				>
					<SendIcon class="size-3.5" />
					Send to Repeater
				</LoadingButton>
				<LoadingButton loading={scanning} size="sm" onclick={scan}>
					<RadarIcon class="size-3.5" />
					Scan {picked.size}
				</LoadingButton>
			</div>
		</div>
	{/if}

	{#if error}
		<p class="text-destructive border-b px-4 py-2 text-xs">{error}</p>
	{/if}

	{#if connector.unassigned > 0 && connector.unassigned === connector.candidates}
		<p class="text-muted-foreground border-b px-4 py-2 text-xs">
			No target covers these requests. Add one from Discovered.
		</p>
	{/if}

	{#if connectors.queueLoading && rows.length === 0}
		<div class="space-y-2 p-4">
			{#each Array(6) as _, i (i)}
				<Skeleton class="h-11 w-full" />
			{/each}
		</div>
	{:else if rows.length === 0}
		<div class="px-4 py-10">
			<EmptyState icon={RadarIcon} title="No request shapes" />
		</div>
	{:else}
		<table class="w-full table-fixed text-sm">
			<thead>
				<tr class="bg-muted/40 border-b">
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
					<th class="w-20 px-2 py-2"></th>
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
								<Hint text={row.url}>
									{#snippet child(props)}
										<span {...props} class="min-w-0 truncate font-mono text-xs leading-5"
											>{row.path}</span
										>
									{/snippet}
								</Hint>
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
							{#if opened.has(row.id) && row.request_sample}
								<div class="mt-2">
									<CodeBlock code={row.request_sample} lang="http" maxLines={12} />
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
							class="px-4 py-2.5 text-right align-top font-mono text-xs leading-5 tabular-nums {statusTone(
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
						<td class="px-2 py-2 align-top">
							<span class="flex h-6 items-center justify-end gap-0.5">
								{#if row.request_sample}
									<Hint text="Request sample">
										{#snippet child(props)}
											<Button
												{...props}
												variant="ghost"
												size="icon"
												class="size-6"
												onclick={() => toggleSample(row.id)}
											>
												<FileTextIcon class="size-3.5" />
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
												class="size-6"
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
											class="size-6"
											href={row.url}
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
		<div class="border-t px-4 py-2">
			<ResultsPagination
				total={page?.total ?? 0}
				page={pageNumber}
				pageSize={PAGE_SIZE}
				noun="shape"
				plural="shapes"
				selectedCount={picked.size}
				onClearSelection={() => picked.clear()}
				onPage={(next) => (pageNumber = next)}
			/>
		</div>
	{/if}
</Card.Root>
