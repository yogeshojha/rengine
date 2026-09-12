<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import SearchIcon from '@lucide/svelte/icons/search';
	import RadarIcon from '@lucide/svelte/icons/radar';
	import SendIcon from '@lucide/svelte/icons/send';
	import EyeOffIcon from '@lucide/svelte/icons/eye-off';
	import LockIcon from '@lucide/svelte/icons/lock';
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
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import { connectorsApi } from '$lib/api/connectors';
	import { connectors } from '$lib/stores/connectors.svelte';
	import {
		CANDIDATE_STATES,
		CANDIDATE_STATE_LABELS,
		NOTICE_HELP,
		NOTICE_LABELS,
		noticeTone
	} from '$lib/config/connectors';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime } from '$lib/utilities/dates';
	import type { Connector } from '$lib/types/connector';

	let { connector, projectId }: { connector: Connector; projectId: string } = $props();

	const HEAD =
		'px-4 py-2 text-left text-2xs font-semibold tracking-wider text-muted-foreground uppercase whitespace-nowrap';

	let stateFilter = $state<string>('new');
	let host = $state<string>('');
	let search = $state('');
	let pageNumber = $state(1);
	const PAGE_SIZE = 50;
	let picked = new SvelteSet<string>();
	let scanning = $state(false);
	let sending = $state(false);
	let sent = $state(0);
	let acting = $state(false);
	let error = $state<string | null>(null);

	const page = $derived(connectors.queue);
	const rows = $derived(page?.rows ?? []);
	const hosts = $derived(page?.hosts ?? []);

	$effect(() => {
		const id = connector.id;
		const filters = {
			state: stateFilter,
			host: host || undefined,
			search: search || undefined,
			page: pageNumber
		};
		untrack(() => {
			picked.clear();
			void connectors.loadQueue(id, projectId, filters);
		});
	});

	$effect(() => {
		void stateFilter;
		void host;
		void search;
		untrack(() => (pageNumber = 1));
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
		await connectors.loadQueue(connector.id, projectId, {
			state: stateFilter,
			host: host || undefined,
			search: search || undefined,
			page: pageNumber
		});
		await connectors.load(projectId, true);
	}

	async function scan() {
		scanning = true;
		error = null;
		try {
			const run = await connectorsApi.scan(connector.id, projectId, [...picked]);
			picked.clear();
			await reload();
			void goto(ROUTES.scan(run.id));
		} catch (e) {
			error = e instanceof Error ? e.message : 'The scan could not be started.';
		} finally {
			scanning = false;
		}
	}

	async function sendToProxy() {
		sending = true;
		error = null;
		try {
			const result = await connectorsApi.send(connector.id, projectId, [...picked]);
			sent = result.queued;
			picked.clear();
			await reload();
		} catch (e) {
			error = e instanceof Error ? e.message : 'They could not be queued.';
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
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead
		title="Queue"
		description="Recorded requests, deduplicated by path and parameter names"
	>
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
			No target covers these yet. Open Discovered to add one; everything recorded here attaches to
			it.
		</p>
	{/if}

	{#if connector.pending_actions > 0}
		<p class="text-muted-foreground border-b px-4 py-2 text-xs">
			{connector.pending_actions} waiting to be collected by Burp.
		</p>
	{:else if sent > 0}
		<p class="text-muted-foreground border-b px-4 py-2 text-xs">
			{sent} sent to Repeater.
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
			<EmptyState
				icon={RadarIcon}
				title="No request shapes"
				description="Request shapes appear as the connector receives proxied traffic."
			/>
		</div>
	{:else}
		<table class="w-full table-fixed text-sm">
			<thead>
				<tr class="bg-muted/40 border-b">
					<th class="w-10 px-4 py-2">
						<Checkbox
							checked={picked.size === rows.length && rows.length > 0}
							onCheckedChange={toggleAll}
							aria-label="Select all"
						/>
					</th>
					<th class="{HEAD} w-16">Method</th>
					<th class={HEAD}>Shape</th>
					<th class="{HEAD} w-20 text-right">Params</th>
					<th class="{HEAD} w-16 text-right">Status</th>
					<th class="{HEAD} w-24 text-right">Seen</th>
				</tr>
			</thead>
			<tbody>
				{#each rows as row (row.id)}
					<tr class="border-b last:border-b-0">
						<td class="px-4 py-2.5 align-top">
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
									<Hint text="The request carried a session">
										{#snippet child(props)}
											<span {...props} class="flex h-5 shrink-0 items-center">
												<LockIcon class="text-muted-foreground size-3" />
											</span>
										{/snippet}
									</Hint>
								{/if}
								<Hint text={row.url}>
									{#snippet child(props)}
										<span {...props} class="min-w-0 truncate font-mono text-xs leading-5">
											{#if !host && hosts.length > 1}<span class="text-muted-foreground"
													>{row.host}</span
												>{/if}{row.path}
										</span>
									{/snippet}
								</Hint>
							</div>
							{#if row.notices.length > 0 || row.title}
								<div class="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-2">
									{#each row.notices as notice (notice)}
										<Hint text={NOTICE_HELP[notice] ?? ''}>
											{#snippet child(props)}
												<span {...props} class="text-2xs {noticeTone(notice)}">
													{NOTICE_LABELS[notice] ?? notice}
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
						<td class="px-4 py-2.5 text-right align-top">
							{#if row.param_count > 0}
								<Hint text={row.params.join(', ')}>
									{#snippet child(props)}
										<span {...props} class="text-muted-foreground text-2xs leading-5 tabular-nums">
											{row.param_count}
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
							class="text-muted-foreground px-4 py-2.5 text-right align-top text-2xs leading-5 whitespace-nowrap"
							>{relativeTime(row.last_seen_at)}</td
						>
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
		<div class="text-muted-foreground border-t px-4 py-2.5 text-xs">
			{page?.total ?? 0} shapes · {connector.requests_seen.toLocaleString()} requests received · {connector.dropped_out_of_scope.toLocaleString()}
			out of scope
		</div>
	{/if}
</Card.Root>
