<script lang="ts">
	import SevCountChip from '$lib/components/sev-count-chip.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Button } from '$lib/components/ui/button';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ActivityLanes from './activity-lanes.svelte';
	import { SEVERITY_LABELS, Severity } from '$lib/config/vulnerabilities';
	import { Fact, NewKind, Signal, type NewKindKey, type SignalKey } from '$lib/config/whats-new';
	import type { NewFeed } from '$lib/types/whats-new';

	interface Props {
		feed: NewFeed | null;
		kinds: NewKindKey[];
		period: string;
		active: SignalKey | null;
		from: string | null;
		to: string | null;
		onSignal: (signal: SignalKey | null) => void;
		onPick: (from: string | null, to: string | null) => void;
		/** The feed did not load; without `onRetry` the page shows the Retry. */
		failed?: boolean;
		onRetry?: () => void;
	}

	let {
		feed,
		kinds,
		period,
		active,
		from,
		to,
		onSignal,
		onPick,
		failed = false,
		onRetry
	}: Props = $props();

	const FINDINGS = [
		{ signal: Signal.CRITICAL, sev: Severity.CRITICAL },
		{ signal: Signal.HIGH, sev: Severity.HIGH }
	];

	let facts = $derived(feed?.facts[NewKind.FINDING] ?? {});
	let kev = $derived(facts[Fact.KEV] ?? 0);
</script>

{#if !feed && failed}
	<div class="flex flex-wrap items-center gap-x-2 gap-y-1 border-b px-4 py-3 text-sm">
		<TriangleAlert class="size-4 shrink-0 text-warning" strokeWidth={1.5} />
		<span class="text-muted-foreground">Activity not loaded</span>
		{#if onRetry}
			<span class="text-muted-foreground" aria-hidden="true">·</span>
			<Button variant="link" size="sm" class="h-auto p-0" onclick={onRetry}>Retry</Button>
		{/if}
	</div>
{:else if !feed}
	<div class="flex flex-wrap items-start gap-x-8 gap-y-4 border-b px-4 py-4" aria-busy="true">
		<div class="flex w-56 flex-col gap-2">
			<Skeleton class="h-3 w-32" />
			<Skeleton class="h-9 w-24" />
			<div class="flex gap-1.5"><Skeleton class="h-8 w-24" /><Skeleton class="h-8 w-20" /></div>
		</div>
		<div class="flex min-w-0 flex-1 flex-col gap-2 pt-1">
			{#each { length: 3 } as _, i (i)}
				<Skeleton class="h-4 w-full rounded-full" />
			{/each}
		</div>
	</div>
{:else}
	<div class="flex flex-col gap-4 border-b px-4 py-4 md:flex-row md:items-start md:gap-8">
		<div class="flex shrink-0 flex-col gap-2 md:w-56">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">{period}</span>
			<div class="flex items-baseline gap-2">
				<span class="font-mono text-4xl leading-none font-semibold tabular-nums">
					{feed.events.toLocaleString()}
				</span>
				<span class="text-sm text-muted-foreground">
					{feed.events === 1 ? 'event' : 'events'}
				</span>
			</div>
			{#if kinds.includes(NewKind.FINDING)}
				<div class="flex flex-wrap items-center gap-1.5">
					{#each FINDINGS as f (f.signal)}
						{@const on = active === f.signal}
						{@const n = facts[f.signal] ?? 0}
						<SevCountChip
							severity={f.sev}
							count={n}
							pressed={on}
							aria-label="New {SEVERITY_LABELS[f.sev].toLowerCase()} findings: {n}"
							onclick={() => onSignal(on ? null : f.signal)}
						/>
					{/each}
				</div>
				{#if kev}
					<span class="text-2xs text-muted-foreground">{kev.toLocaleString()} known exploited</span>
				{/if}
			{/if}
		</div>

		<ActivityLanes
			days={feed.daily}
			{kinds}
			counts={feed.counts}
			periodStart={from ? null : feed.since}
			periodEnd={feed.until}
			markedAt={feed.marked_at}
			{from}
			{to}
			{active}
			{onPick}
			{onSignal}
		/>
	</div>
{/if}
