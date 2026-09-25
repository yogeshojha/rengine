<script lang="ts">
	import ActivityIcon from '@lucide/svelte/icons/activity';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import XIcon from '@lucide/svelte/icons/x';
	import * as Accordion from '$lib/components/ui/accordion';
	import { Button } from '$lib/components/ui/button';
	import EmptyState from '$lib/components/empty-state.svelte';
	import {
		dayLabel,
		groupBursts,
		inAppHref,
		isChange,
		parseClient,
		spanLabel,
		timeOfDay,
		timeWithSeconds
	} from '$lib/utilities/mcp';
	import { TOUCHES_TARGETS, type McpCall, type McpCapability } from '$lib/types/mcp';

	interface Props {
		calls: McpCall[];
		titles: Map<string, string>;
	}

	let { calls, titles }: Props = $props();

	const PAGE = 20;
	const FILTERS = [
		{ key: 'all', label: 'All' },
		{ key: 'changes', label: 'Changes' },
		{ key: 'failed', label: 'Refused or failed' }
	] as const;
	type Filter = (typeof FILTERS)[number]['key'];
	const PILL =
		'inline-flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none';

	let filter = $state<Filter>('all');
	let shown = $state(PAGE);
	let open = $state<string[]>([]);

	const counts = $derived<Record<Filter, number>>({
		all: calls.length,
		changes: calls.filter(isChange).length,
		failed: calls.filter((c) => !c.ok).length
	});
	const kept = $derived(
		calls.filter((c) => filter === 'all' || (filter === 'changes' ? isChange(c) : !c.ok))
	);
	const bursts = $derived(groupBursts(kept));
	const page = $derived(bursts.slice(0, shown));

	const dot = (c: McpCall) =>
		c.capability === 'plan' ? 'bg-info' : isChange(c) ? 'bg-warning' : 'bg-muted-foreground/50';
	const effect = (c: McpCall) =>
		TOUCHES_TARGETS.includes(c.capability as McpCapability) ? 'sent traffic' : 'changed data';

	function choose(key: Filter) {
		filter = key;
		shown = PAGE;
	}
</script>

{#if !calls.length}
	<div class="p-5">
		<EmptyState compact icon={ActivityIcon} title="No calls" />
	</div>
{:else}
	<div class="flex flex-wrap items-center gap-1.5 border-b px-5 py-2.5">
		{#each FILTERS as f (f.key)}
			{@const n = counts[f.key]}
			<button
				type="button"
				class="{PILL} {filter === f.key
					? 'border-foreground/40 bg-muted'
					: 'border-border hover:border-foreground/30'}"
				aria-pressed={filter === f.key}
				onclick={() => choose(f.key)}
			>
				<span class="text-muted-foreground">{f.label}</span>
				<span
					class="font-mono font-semibold tabular-nums {n && f.key === 'changes'
						? 'text-warning'
						: n && f.key === 'failed'
							? 'text-destructive'
							: ''}">{n}</span
				>
			</button>
		{/each}
	</div>

	{#if !bursts.length}
		<div class="p-5">
			<EmptyState compact icon={ActivityIcon} title="No calls match" />
		</div>
	{:else}
		<Accordion.Root type="multiple" bind:value={open}>
			{#each page as burst (burst.key)}
				{@const client = parseClient(burst.client)}
				<Accordion.Item value={burst.key} class="border-b last:border-b-0">
					<Accordion.Trigger
						class="items-start gap-3 rounded-none px-5 py-3 hover:bg-muted/40 hover:no-underline"
					>
						<span class="flex min-w-0 flex-1 flex-col gap-0.5 text-left">
							<span class="flex flex-wrap items-baseline gap-x-2.5 leading-5">
								<span class="text-sm font-medium">
									{dayLabel(burst.ended)}
									{timeOfDay(burst.started)}
								</span>

								<span class="text-xs font-normal text-muted-foreground">
									{client.name}{#if client.version}
										<span class="ml-1 font-mono">{client.version}</span>{/if}
								</span>
							</span>
							<span class="text-xs font-normal text-muted-foreground tabular-nums">
								{burst.calls.length} call{burst.calls.length === 1 ? '' : 's'} · {spanLabel(
									burst.spanMs
								)}
							</span>
						</span>
						<span class="flex h-5 shrink-0 items-center gap-3 text-xs font-normal">
							{#if burst.changes}
								<span class="flex items-center gap-1 text-warning tabular-nums">
									<TriangleAlertIcon class="size-3.5" />
									{burst.changes} change{burst.changes === 1 ? '' : 's'}
								</span>
							{/if}
							{#if burst.failed}
								<span class="text-destructive tabular-nums">{burst.failed} failed</span>
							{/if}
						</span>
					</Accordion.Trigger>
					<Accordion.Content class="pb-2">
						<div class="flex flex-col pr-5 pl-12">
							{#each burst.calls as call, i (call.at + call.tool + i)}
								{@const title = titles.get(call.tool) ?? call.tool}
								<div
									class="grid grid-cols-[4.25rem_0.75rem_minmax(0,1fr)_auto] items-start gap-x-2.5 border-t border-border/60 py-2 first:border-t-0"
								>
									<span class="font-mono text-2xs leading-5 text-muted-foreground tabular-nums">
										{timeWithSeconds(call.at)}
									</span>
									<span class="flex h-5 items-center justify-center">
										{#if call.ok}
											<span class="size-1.5 rounded-full {dot(call)}" aria-hidden="true"></span>
										{:else}
											<XIcon class="size-3 text-destructive" aria-label="Failed" />
										{/if}
									</span>
									<span class="flex min-w-0 flex-col gap-0.5">
										<span class="flex flex-wrap items-baseline gap-x-2 gap-y-1 leading-5">
											<span class="text-sm {isChange(call) ? 'font-medium' : ''}">{title}</span>
											{#if call.args}
												<code
													class="rounded border bg-muted/50 px-1.5 font-mono text-xs wrap-anywhere"
													>{call.args}</code
												>
											{/if}
										</span>
										<span class="text-xs leading-snug wrap-anywhere">
											{#if call.ok}
												{#if call.summary}<span>{call.summary}</span>{/if}
											{:else}
												<span class="text-destructive">
													{call.refused ? 'Refused.' : ''}
													{call.detail ?? 'Failed'}
												</span>
											{/if}
										</span>
										<span class="font-mono text-2xs text-muted-foreground">
											{call.tool}{#if isChange(call)}
												<span class="font-sans text-warning"> · {effect(call)}</span>{/if}
										</span>
									</span>
									{#if call.ok && call.pivot}
										<a
											href={inAppHref(call.pivot)}
											class="inline-flex h-5 items-center gap-0.5 rounded px-1 text-xs text-primary hover:bg-muted"
										>
											Open
											<ArrowUpRight class="size-3" />
										</a>
									{:else}
										<span></span>
									{/if}
								</div>
							{/each}
						</div>
					</Accordion.Content>
				</Accordion.Item>
			{/each}
		</Accordion.Root>
		{#if bursts.length > shown}
			<div class="border-t px-5 py-2.5">
				<Button variant="ghost" size="sm" onclick={() => (shown += PAGE)}>
					Show {Math.min(PAGE, bursts.length - shown)} more sessions
				</Button>
			</div>
		{/if}
	{/if}
{/if}
