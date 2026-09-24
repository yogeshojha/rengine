<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import ActivityLanes from './activity-lanes.svelte';
	import { SEVERITY_CHIP, SEVERITY_LABELS, Severity } from '$lib/config/vulnerabilities';
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
	}

	let { feed, kinds, period, active, from, to, onSignal, onPick }: Props = $props();

	const FINDINGS = [
		{ signal: Signal.CRITICAL, sev: Severity.CRITICAL },
		{ signal: Signal.HIGH, sev: Severity.HIGH }
	];

	let facts = $derived(feed?.facts[NewKind.FINDING] ?? {});
	let kev = $derived(facts[Fact.KEV] ?? 0);
</script>

{#if !feed}
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
						<button
							type="button"
							class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 font-mono text-sm font-semibold tabular-nums transition-shadow focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {SEVERITY_CHIP[
								f.sev
							].chip} {on ? 'ring-2 ring-current/50' : ''} {n ? '' : 'opacity-45'}"
							aria-pressed={on}
							aria-label="New {SEVERITY_LABELS[f.sev].toLowerCase()} findings: {n}"
							onclick={() => onSignal(on ? null : f.signal)}
						>
							<span class="text-2xs font-medium opacity-70">{SEVERITY_LABELS[f.sev]}</span>
							{n.toLocaleString()}
						</button>
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
