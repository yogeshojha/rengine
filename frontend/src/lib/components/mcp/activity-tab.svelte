<script lang="ts">
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import SearchX from '@lucide/svelte/icons/search-x';
	import X from '@lucide/svelte/icons/x';
	import * as Accordion from '$lib/components/ui/accordion';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ResultsPagination from '$lib/components/scans/results/table/results-pagination.svelte';
	import { mcp } from '$lib/stores/mcp.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		agentKey,
		dayLabel,
		durationLabel,
		groupBursts,
		median,
		parseClient,
		spanLabel,
		tally,
		tallyAgents,
		timeOfDay,
		timeWithSeconds,
		TRAIL_CAP,
		trailStart
	} from '$lib/utilities/mcp';

	interface Props {
		now: number;
	}

	let { now }: Props = $props();

	const ALL = 'all';
	const FAILED = 'failed';
	const TABS = [
		{ key: ALL, label: 'All calls' },
		{ key: FAILED, label: 'Failed' }
	];
	const LABEL = 'text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase';
	const CHIP_LIMIT = 5;
	const RANK_LIMIT = 8;
	const SESSION_PAGE = 20;
	const CALL_PAGE = 25;

	let outcome = $state<string>(ALL);
	let search = $state('');
	let tool = $state<string | null>(null);
	let agent = $state<string | null>(null);
	let openItems = $state<string[]>([]);
	let page = $state(0);
	let revealed = $state<Record<string, number>>({});
	let allTools = $state(false);

	const calls = $derived(mcp.calls);
	const failedTotal = $derived(calls.filter((c) => !c.ok).length);
	const counts = $derived({ [ALL]: calls.length, [FAILED]: failedTotal });
	const typical = $derived(median(calls.map((c) => c.duration_ms)));
	const byTool = $derived(tally(calls));
	const byAgent = $derived(tallyAgents(calls));
	const maxTool = $derived(byTool[0]?.count ?? 1);

	const filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return calls.filter(
			(c) =>
				(outcome !== FAILED || !c.ok) &&
				(!tool || c.tool === tool) &&
				(!agent || agentKey(c.client, c.token_name) === agent) &&
				(!q ||
					c.tool.includes(q) ||
					c.token_name.toLowerCase().includes(q) ||
					c.client.toLowerCase().includes(q) ||
					(c.detail ?? '').toLowerCase().includes(q))
		);
	});
	const bursts = $derived(groupBursts(filtered));
	const pageCount = $derived(Math.max(1, Math.ceil(bursts.length / SESSION_PAGE)));
	const safePage = $derived(Math.min(page, pageCount - 1));
	const pageBursts = $derived(bursts.slice(safePage * SESSION_PAGE, (safePage + 1) * SESSION_PAGE));
	const oldest = $derived(calls.length ? calls[calls.length - 1].at : null);
	const trailFull = $derived(trailStart(calls) !== null);
	const rankedTools = $derived(allTools ? byTool : byTool.slice(0, RANK_LIMIT));
	const narrowed = $derived(outcome === FAILED || !!tool || !!agent || !!search.trim());
	const loadedAgo = $derived(
		mcp.callsLoadedAt ? Math.round((now - mcp.callsLoadedAt) / 1000) : null
	);

	$effect(() => {
		void [outcome, search, tool, agent];
		page = 0;
	});

	function clear() {
		outcome = ALL;
		search = '';
		tool = null;
		agent = null;
	}

	function reveal(key: string) {
		revealed[key] = (revealed[key] ?? 0) + CALL_PAGE;
	}
</script>

<Card.Root class="gap-0 py-0">
	<div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-b px-2">
		<CountTabs tabs={TABS} value={outcome} {counts} onChange={(k) => (outcome = k)} />
		<div class="flex items-center gap-2 pr-3 pb-1.5">
			<Input
				bind:value={search}
				placeholder="Filter by tool, agent or error"
				class="h-8 w-full sm:w-60"
				aria-label="Filter calls"
			/>
			<Hint
				text={loadedAgo === null ? 'Refresh' : `Updated ${loadedAgo}s ago · refreshes every 10 s`}
			>
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-8"
						onclick={() => mcp.loadCalls()}
					>
						<RefreshCwIcon class="size-4" />
						<span class="sr-only">Refresh</span>
					</Button>
				{/snippet}
			</Hint>
		</div>
	</div>

	{#if tool || agent}
		<div class="flex flex-wrap items-center gap-2 border-b px-5 py-2 text-xs">
			{#if tool}
				<button
					type="button"
					class="inline-flex h-6 items-center gap-1 rounded-md border bg-muted/50 px-2 font-mono hover:bg-muted"
					onclick={() => (tool = null)}
				>
					{tool}
					<X class="size-3 text-muted-foreground" />
				</button>
			{/if}
			{#if agent}
				{@const [client, token] = agent.split('|')}
				<button
					type="button"
					class="inline-flex h-6 items-center gap-1 rounded-md border bg-muted/50 px-2 hover:bg-muted"
					onclick={() => (agent = null)}
				>
					{parseClient(client).name}
					<span class="font-mono text-muted-foreground">{token}</span>
					<X class="size-3 text-muted-foreground" />
				</button>
			{/if}
			<span class="text-muted-foreground tabular-nums">
				{filtered.length} of {calls.length} calls
			</span>
		</div>
	{/if}

	<div class="grid lg:grid-cols-[minmax(0,1fr)_16rem]">
		<div class="flex min-w-0 flex-col lg:border-r">
			{#if calls.length === 0}
				<div class="p-5">
					<EmptyState
						compact
						icon={ActivityIcon}
						title="No calls yet"
						description="Tool calls appear here once an agent connects."
					/>
				</div>
			{:else if bursts.length === 0}
				<div class="p-5">
					<EmptyState compact icon={SearchX} title="No calls match" description="Remove a filter.">
						<Button variant="outline" size="sm" onclick={clear}>Clear filters</Button>
					</EmptyState>
				</div>
			{:else}
				<Accordion.Root type="multiple" bind:value={openItems}>
					{#each pageBursts as burst, i (burst.key)}
						{@const client = parseClient(burst.client)}
						{@const day = dayLabel(burst.ended)}
						{@const newDay = i === 0 || dayLabel(pageBursts[i - 1].ended) !== day}
						{@const ordered = [...burst.calls].reverse()}
						{@const shown = CALL_PAGE + (revealed[burst.key] ?? 0)}
						{@const remaining = Math.max(0, ordered.length - shown)}
						{#if newDay}
							<div
								class="border-b bg-muted/30 px-5 py-1.5 text-[11px] font-semibold tracking-[0.08em] text-muted-foreground uppercase"
							>
								{day}
							</div>
						{/if}
						<Accordion.Item value={burst.key}>
							<Accordion.Trigger
								class="items-center gap-3 rounded-none px-5 py-2.5 hover:bg-muted/40 hover:no-underline"
							>
								<span class="flex h-5 shrink-0 items-center">
									<span
										class="size-2 rounded-full {burst.failed ? 'bg-destructive' : 'bg-success'}"
										aria-hidden="true"
									></span>
								</span>
								<span class="flex min-w-0 flex-1 flex-col gap-1">
									<span class="flex flex-wrap items-center gap-x-2 gap-y-0.5 leading-5">
										<span class="text-sm font-medium">{client.name}</span>
										<span class="font-mono text-xs font-normal text-muted-foreground">
											{burst.token}
										</span>
										<span class="text-xs font-normal text-muted-foreground tabular-nums">
											{burst.calls.length}
											{burst.calls.length === 1 ? 'call' : 'calls'}{#if burst.failed}<span
													class="ml-1 text-destructive">· {burst.failed} failed</span
												>{/if}
										</span>
										<span class="font-mono text-xs font-normal text-muted-foreground tabular-nums">
											{timeOfDay(burst.started)}{#if burst.calls.length > 1}–{timeOfDay(
													burst.ended
												)} ·
												{spanLabel(burst.spanMs)}{/if}
										</span>
									</span>
									<span class="flex flex-wrap items-center gap-1">
										{#each burst.tools.slice(0, CHIP_LIMIT) as t (t.name)}
											<span
												class="inline-flex h-5 items-center gap-1 rounded border bg-muted/40 px-1.5 font-mono text-[11px] leading-none font-normal"
											>
												{t.name}{#if t.count > 1}<span class="text-muted-foreground tabular-nums"
														>×{t.count}</span
													>{/if}
											</span>
										{/each}
										{#if burst.tools.length > CHIP_LIMIT}
											<span class="text-[11px] font-normal text-muted-foreground">
												+{burst.tools.length - CHIP_LIMIT} more
											</span>
										{/if}
									</span>
								</span>
								<span class="shrink-0 text-xs font-normal text-muted-foreground">
									{relativeTime(burst.ended)}
								</span>
							</Accordion.Trigger>
							<Accordion.Content class="pb-0">
								<div class="divide-y border-t bg-muted/20">
									{#each ordered.slice(0, shown) as call (call.at + call.tool)}
										<div class="flex flex-col gap-1 py-2 pr-5 pl-10">
											<div class="flex items-center gap-3">
												<span
													class="w-16 shrink-0 font-mono text-xs text-muted-foreground tabular-nums"
												>
													{timeWithSeconds(call.at)}
												</span>
												<span class="flex h-5 shrink-0 items-center">
													<span
														class="size-1.5 rounded-full {call.ok
															? 'bg-success'
															: 'bg-destructive'}"
														aria-hidden="true"
													></span>
												</span>
												<button
													type="button"
													class="min-w-0 truncate font-mono text-sm hover:underline"
													onclick={() => (tool = call.tool)}
												>
													{call.tool}
												</button>
												<span
													class="ml-auto shrink-0 font-mono text-xs text-muted-foreground tabular-nums"
												>
													{durationLabel(call.duration_ms)}
												</span>
											</div>
											{#if !call.ok && call.detail}
												<p
													class="ml-[6.25rem] border-l-2 border-destructive/40 pl-3 text-xs leading-snug text-muted-foreground wrap-anywhere"
												>
													{call.detail}
												</p>
											{/if}
										</div>
									{/each}
									{#if remaining}
										<div class="flex items-center gap-1.5 py-2 pr-5 pl-10 text-xs">
											<button
												type="button"
												class="font-medium text-primary hover:underline"
												onclick={() => reveal(burst.key)}
											>
												Show {Math.min(remaining, CALL_PAGE)} more
											</button>
											<span class="text-muted-foreground">· {remaining} remaining</span>
										</div>
									{/if}
								</div>
							</Accordion.Content>
						</Accordion.Item>
					{/each}
				</Accordion.Root>
				{#if bursts.length > SESSION_PAGE}
					<ResultsPagination
						total={bursts.length}
						page={safePage}
						pageSize={SESSION_PAGE}
						noun="session"
						onPage={(p) => (page = p)}
					/>
				{/if}
				<p class="border-t px-5 py-3 text-xs text-muted-foreground">
					{bursts.length}
					{bursts.length === 1 ? 'session' : 'sessions'} from {filtered.length}
					{#if narrowed}of {calls.length}{/if}
					calls. Calls from one agent closer than five minutes apart form a session. The trail keeps the
					last {TRAIL_CAP} calls for seven days{#if trailFull && oldest}; the oldest kept is from
						{dayLabel(oldest).toLowerCase()} at {timeOfDay(oldest)}{/if}.
				</p>
			{/if}
		</div>

		{#if calls.length}
			<aside
				class="flex flex-col divide-y border-t px-5 py-5 lg:sticky lg:top-4 lg:self-start lg:border-t-0"
			>
				<div class="flex flex-col gap-1.5 pb-4">
					<h4 class="mb-1 {LABEL}">Trail</h4>
					<div class="grid grid-cols-[4.25rem_minmax(0,1fr)] gap-2 text-[13px]">
						<span class="pt-px text-xs text-muted-foreground">Calls</span>
						<span class="tabular-nums">
							{calls.length}{#if failedTotal}<span class="ml-1 text-destructive"
									>· {failedTotal} failed</span
								>{/if}
						</span>
						<span class="pt-px text-xs text-muted-foreground">Typical</span>
						<span class="tabular-nums">{typical === null ? '—' : durationLabel(typical)}</span>
						<span class="pt-px text-xs text-muted-foreground">Newest</span>
						<span>{relativeTime(calls[0].at)}</span>
						<span class="pt-px text-xs text-muted-foreground">Oldest</span>
						<span>
							{relativeTime(oldest)}{#if trailFull}<span class="ml-1 text-muted-foreground"
									>· trail full</span
								>{/if}
						</span>
					</div>
				</div>

				<div class="flex flex-col gap-1.5 py-4">
					<h4 class="mb-1 flex items-baseline gap-2 {LABEL}">
						By tool
						<span class="text-xs font-medium tracking-normal normal-case tabular-nums">
							{byTool.length}
						</span>
					</h4>
					{#each rankedTools as t (t.name)}
						<button
							type="button"
							class="group flex flex-col gap-1 text-left"
							aria-pressed={tool === t.name}
							onclick={() => (tool = tool === t.name ? null : t.name)}
						>
							<span class="flex items-baseline justify-between gap-2 text-[13px]">
								<span
									class="min-w-0 truncate font-mono text-xs group-hover:underline {tool === t.name
										? 'font-medium'
										: ''}"
								>
									{t.name}
								</span>
								<span class="shrink-0 text-xs text-muted-foreground tabular-nums">{t.count}</span>
							</span>
							<span class="h-1 w-full overflow-hidden rounded-full bg-muted">
								<span
									class="block h-full rounded-full bg-chart-1 {tool && tool !== t.name
										? 'opacity-40'
										: ''}"
									style="width: {(t.count / maxTool) * 100}%"
								></span>
							</span>
						</button>
					{/each}
					{#if byTool.length > RANK_LIMIT}
						<button
							type="button"
							class="self-start text-xs font-medium text-primary hover:underline"
							onclick={() => (allTools = !allTools)}
						>
							{allTools ? 'Show fewer' : `Show ${byTool.length - RANK_LIMIT} more`}
						</button>
					{/if}
				</div>

				<div class="flex flex-col gap-1.5 pt-4">
					<h4 class="mb-1 flex items-baseline gap-2 {LABEL}">
						By agent
						<span class="text-xs font-medium tracking-normal normal-case tabular-nums">
							{byAgent.length}
						</span>
					</h4>
					{#each byAgent as a (a.key)}
						{@const c = parseClient(a.client)}
						<button
							type="button"
							class="group flex items-baseline justify-between gap-2 text-left text-[13px]"
							aria-pressed={agent === a.key}
							onclick={() => (agent = agent === a.key ? null : a.key)}
						>
							<span
								class="min-w-0 truncate group-hover:underline {agent === a.key
									? 'font-medium'
									: ''}"
							>
								{c.name}
								<span class="font-mono text-xs text-muted-foreground">{a.token}</span>
							</span>
							<span class="shrink-0 text-xs text-muted-foreground tabular-nums">{a.count}</span>
						</button>
					{/each}
				</div>
			</aside>
		{/if}
	</div>
</Card.Root>
