<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { SEVERITY_CHIP, SEVERITY_LABELS, Severity } from '$lib/config/vulnerabilities';
	import {
		SIGNAL_LABELS,
		type SignalFilter,
		type TargetSummary
	} from '$lib/utilities/target-signals';

	interface Props {
		loading?: boolean;
		summary: TargetSummary;
		live: number;
		active: SignalFilter | null;
		onSignal: (signal: SignalFilter | null) => void;
	}

	let { loading = false, summary, live, active, onSignal }: Props = $props();

	const FINDINGS: { signal: SignalFilter; sev: string }[] = [
		{ signal: 'critical', sev: Severity.CRITICAL },
		{ signal: 'high', sev: Severity.HIGH },
		{ signal: 'medium', sev: Severity.MEDIUM }
	];
	const ENRICHMENT: { signal: SignalFilter; tone: string }[] = [
		{ signal: 'attention', tone: 'text-destructive' },
		{ signal: 'expiring', tone: 'text-warning' },
		{ signal: 'awaiting', tone: 'text-info' },
		{ signal: 'monitored', tone: 'text-foreground' }
	];
</script>

{#snippet stat(label: string, signal: SignalFilter | null, n: number, tone: string, sub = '')}
	{@const on = signal === null ? active === null : active === signal}
	<button
		type="button"
		class="-mx-2 -my-1 flex flex-col items-start gap-0.5 rounded-md px-2 py-1 text-left transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
		aria-pressed={on}
		onclick={() => onSignal(signal === null || on ? null : signal)}
	>
		<span class="text-2xs tracking-wide text-muted-foreground uppercase">{label}</span>
		<span
			class="font-mono text-2xl font-semibold tabular-nums {n
				? tone
				: 'text-muted-foreground/60'} {on && signal !== null
				? 'underline decoration-2 underline-offset-4'
				: ''}"
		>
			{n.toLocaleString()}
		</span>
		{#if sub}<span class="text-2xs text-muted-foreground">{sub}</span>{/if}
	</button>
{/snippet}

{#if loading}
	<div class="flex flex-wrap items-start gap-x-8 gap-y-4 border-b px-4 py-4" aria-busy="true">
		{#each ['w-16', 'w-20', 'w-24'] as w (w)}
			<div class="flex flex-col gap-1.5">
				<Skeleton class="h-3 {w}" />
				<Skeleton class="h-7 w-10" />
			</div>
		{/each}
		<div class="flex flex-col gap-1.5">
			<Skeleton class="h-3 w-20" />
			<div class="flex gap-1.5">
				<Skeleton class="h-8 w-20 rounded-md" />
				<Skeleton class="h-8 w-16 rounded-md" />
				<Skeleton class="h-8 w-20 rounded-md" />
			</div>
		</div>
		<div class="flex flex-col gap-1.5 lg:ml-auto">
			<Skeleton class="h-3 w-20" />
			<div class="flex gap-1.5">
				{#each ['w-32', 'w-20', 'w-24', 'w-24'] as w, i (i)}
					<Skeleton class="h-8 {w} rounded-md" />
				{/each}
			</div>
		</div>
	</div>
{:else}
	<div class="flex flex-wrap items-start gap-x-8 gap-y-4 border-b px-4 py-4">
		{@render stat(
			'Targets',
			null,
			summary.total,
			'text-foreground',
			live ? `${live} scanning` : ''
		)}
		{@render stat(SIGNAL_LABELS.unscanned, 'unscanned', summary.unscanned, 'text-foreground')}
		{@render stat(SIGNAL_LABELS.stale, 'stale', summary.stale, 'text-warning')}
		<div class="flex flex-col gap-1">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">With findings</span>
			<div class="flex items-center gap-1.5">
				{#each FINDINGS as f (f.signal)}
					{@const on = active === f.signal}
					<button
						type="button"
						class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 font-mono text-sm font-semibold tabular-nums transition-shadow focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {SEVERITY_CHIP[
							f.sev
						].chip} {on ? 'ring-2 ring-current/50' : ''} {summary[f.signal] ? '' : 'opacity-45'}"
						aria-pressed={on}
						aria-label="Targets with {SEVERITY_LABELS[f.sev].toLowerCase()} findings: {summary[
							f.signal
						]}"
						onclick={() => onSignal(on ? null : f.signal)}
					>
						<span class="text-2xs font-medium opacity-70">{SEVERITY_LABELS[f.sev]}</span>
						{summary[f.signal].toLocaleString()}
					</button>
				{/each}
			</div>
		</div>
		<div class="flex flex-col gap-1 lg:ml-auto">
			<span class="text-2xs tracking-wide text-muted-foreground uppercase">Enrichment</span>
			<div class="flex flex-wrap items-center gap-1.5">
				{#each ENRICHMENT as e (e.signal)}
					{@const on = active === e.signal}
					{@const n = summary[e.signal]}
					<button
						type="button"
						class="inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {on
							? 'border-foreground/40 bg-muted'
							: 'border-border hover:border-foreground/30'} {n ? '' : 'opacity-50'}"
						aria-pressed={on}
						onclick={() => onSignal(on ? null : e.signal)}
					>
						<span class="text-muted-foreground">{SIGNAL_LABELS[e.signal]}</span>
						<span class="font-mono font-semibold tabular-nums {n ? e.tone : ''}"
							>{n.toLocaleString()}</span
						>
					</button>
				{/each}
			</div>
		</div>
	</div>
{/if}
