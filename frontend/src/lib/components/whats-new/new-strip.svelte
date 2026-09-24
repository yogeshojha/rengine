<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as ScrollArea from '$lib/components/ui/scroll-area';
	import ActivityGrid from './activity-grid.svelte';
	import { SEVERITY_CHIP, SEVERITY_LABELS, Severity } from '$lib/config/vulnerabilities';
	import {
		Fact,
		KIND_LABELS,
		NewKind,
		Signal,
		type NewKindKey,
		type SignalKey
	} from '$lib/config/whats-new';
	import type { NewFeed } from '$lib/types/whats-new';

	interface Props {
		feed: NewFeed | null;
		kinds: readonly string[];
		since: string;
		active: SignalKey | null;
		gridKinds: NewKindKey[];
		from: string | null;
		to: string | null;
		onSignal: (signal: SignalKey | null) => void;
		onPick: (from: string | null, to: string | null) => void;
	}

	let { feed, kinds, since, active, gridKinds, from, to, onSignal, onPick }: Props = $props();

	const FINDINGS = [
		{ signal: Signal.CRITICAL, sev: Severity.CRITICAL },
		{ signal: Signal.HIGH, sev: Severity.HIGH }
	];

	let counts = $derived(feed?.counts ?? {});
	let facts = $derived(feed?.facts ?? {});
	function fact(kind: string, key: string): number {
		return facts[kind]?.[key] ?? 0;
	}
	function shows(kind: string): boolean {
		return kinds.includes(kind);
	}
	const BOUNTY_STATS: NewKindKey[] = [
		NewKind.PROGRAM,
		NewKind.SCOPE,
		NewKind.OUT_OF_SCOPE,
		NewKind.BOUNTY_TABLE,
		NewKind.RULES,
		NewKind.CERT_HOST,
		NewKind.TARGET
	];
	let bountyStats = $derived(
		BOUNTY_STATS.filter((k) => shows(k) && (counts[k] ?? 0) > 0).map((kind) => ({
			kind,
			sub:
				kind === NewKind.SCOPE && fact(kind, Fact.NOT_TARGET)
					? `${fact(kind, Fact.NOT_TARGET).toLocaleString()} not targets`
					: kind === NewKind.CERT_HOST && fact(kind, Fact.ANSWERING)
						? `${fact(kind, Fact.ANSWERING).toLocaleString()} answering`
						: kind === NewKind.TARGET && fact(kind, Fact.NOT_SCANNED)
							? `${fact(kind, Fact.NOT_SCANNED).toLocaleString()} not scanned`
							: ''
		}))
	);
</script>

{#snippet stat(label: string, signal: SignalKey | null, n: number, sub = '', prefix = '')}
	{@const on = signal !== null && active === signal}
	<button
		type="button"
		class="group/s flex flex-col items-start gap-0.5 rounded-md text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
		aria-pressed={on}
		disabled={signal === null}
		onclick={() => onSignal(on ? null : signal)}
	>
		<span class="text-2xs tracking-wide text-muted-foreground uppercase">{label}</span>
		<span
			class="font-mono text-2xl font-semibold tabular-nums underline-offset-4 {signal
				? 'group-hover/s:underline'
				: ''} {n ? 'text-foreground' : 'text-muted-foreground/60'} {on
				? 'underline decoration-2'
				: ''}"
		>
			{n ? prefix : ''}{n.toLocaleString()}
		</span>
		{#if sub}<span class="text-2xs text-muted-foreground">{sub}</span>{/if}
	</button>
{/snippet}

{#if !feed}
	<div class="flex flex-wrap items-start gap-x-8 gap-y-4 border-b px-4 py-4" aria-busy="true">
		{#each ['w-14', 'w-24', 'w-28', 'w-16', 'w-20'] as w (w)}
			<div class="flex flex-col gap-1.5">
				<Skeleton class="h-3 {w}" />
				<Skeleton class="h-7 w-12" />
				<Skeleton class="h-3 w-20" />
			</div>
		{/each}
		<Skeleton class="h-[7.5rem] w-full max-w-[42rem] rounded-md lg:ml-auto lg:w-[36rem]" />
	</div>
{:else}
	<div class="flex flex-wrap items-start gap-x-8 gap-y-4 border-b px-4 py-4">
		<div class="flex flex-col gap-0.5">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">Since</span>
			<span class="text-lg leading-8 font-semibold">{since}</span>
		</div>

		{#if shows(NewKind.FINDING)}
			<div class="flex flex-col gap-1">
				<button
					type="button"
					class="w-fit text-left text-2xs tracking-wide text-muted-foreground uppercase hover:text-foreground {active ===
					NewKind.FINDING
						? 'text-foreground underline decoration-2 underline-offset-4'
						: ''}"
					aria-pressed={active === NewKind.FINDING}
					onclick={() => onSignal(active === NewKind.FINDING ? null : NewKind.FINDING)}
				>
					New findings
				</button>
				<div class="flex items-center gap-1.5">
					{#each FINDINGS as f (f.signal)}
						{@const on = active === f.signal}
						{@const n = fact(NewKind.FINDING, f.signal)}
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
				{#if fact(NewKind.FINDING, Fact.KEV)}
					<span class="text-2xs text-muted-foreground">
						{fact(NewKind.FINDING, Fact.KEV).toLocaleString()} known exploited
					</span>
				{/if}
			</div>
		{/if}

		{#each bountyStats as b (b.kind)}
			{@render stat(KIND_LABELS[b.kind], b.kind, counts[b.kind] ?? 0, b.sub)}
		{/each}

		{#if feed.daily.length}
			<div class="flex max-w-full min-w-0 flex-col gap-1 lg:ml-auto">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase">Last 13 weeks</span>
				<ScrollArea.Root orientation="horizontal" class="max-w-full">
					<div class="pb-2">
						<ActivityGrid days={feed.daily} kinds={gridKinds} {from} {to} {onPick} />
					</div>
				</ScrollArea.Root>
			</div>
		{/if}
	</div>
{/if}
