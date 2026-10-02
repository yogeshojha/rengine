<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import Hint from '$lib/components/hint.svelte';
	import { Button } from '$lib/components/ui/button';
	import { findingPrefs } from './prefs.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import {
		SEVERITY_CHIP,
		SEVERITY_LABELS,
		SEVERITY_ORDER,
		Severity
	} from '$lib/config/vulnerabilities';
	import type { ScanVulnerabilities } from '$lib/utilities/vulns';

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const SHOWN = SEVERITY_ORDER.filter((s) => s !== Severity.UNKNOWN && s !== Severity.INFO);
	const BAR = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM];

	interface Props {
		overview: ScanVulnerabilities | null;
		counts: Record<string, number> | null;
		unit: string;
		severities: string[];
		newOn: boolean;
		kevOn: boolean;
		hostOn: (host: string) => boolean;
		onSeverity: (severity: string) => void;
		onNew: () => void;
		onKev: () => void;
		onHost: (host: string) => void;
	}

	let {
		overview,
		counts,
		unit,
		severities,
		newOn,
		kevOn,
		hostOn,
		onSeverity,
		onNew,
		onKev,
		onHost
	}: Props = $props();

	let hosts = $derived(overview?.top_hosts ?? []);
	let max = $derived(Math.max(1, ...hosts.map((h) => h.total)));
	let tested = $derived(overview?.scanned_hosts ?? 0);

	function count(h: (typeof hosts)[number], sev: string): number {
		return h.counts.find((c) => c.severity === sev)?.count ?? 0;
	}
</script>

{#snippet toggle(label: string, n: number, on: boolean, click: () => void, tone: string)}
	<button
		type="button"
		class="-mx-1.5 flex flex-col items-start gap-0.5 rounded-md px-1.5 text-left transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
		aria-pressed={on}
		onclick={click}
	>
		<span class="text-2xs tracking-wide text-muted-foreground uppercase">{label}</span>
		<span
			class="font-mono text-2xl font-semibold tabular-nums underline-offset-4 {n
				? tone
				: 'text-muted-foreground/60'} {on ? 'underline decoration-2' : ''}"
		>
			{n.toLocaleString()}
		</span>
	</button>
{/snippet}

{#snippet sevChip(sev: string, small: boolean)}
	{@const n = counts?.[sev] ?? 0}
	{@const on = severities.includes(sev)}
	<button
		type="button"
		class="inline-flex items-center gap-1.5 rounded-md font-mono font-semibold tabular-nums transition-shadow focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {small
			? 'h-6 px-2 text-xs'
			: 'h-8 px-2.5 text-sm'} {SEVERITY_CHIP[sev].chip} {on ? 'ring-2 ring-current/50' : ''} {n
			? ''
			: 'opacity-45'}"
		aria-pressed={on}
		aria-label="{SEVERITY_LABELS[sev]}: {n}"
		onclick={() => onSeverity(sev)}
	>
		<span class="text-2xs font-medium opacity-70">{SEVERITY_LABELS[sev]}</span>
		{n.toLocaleString()}
	</button>
{/snippet}

{#if !findingPrefs.summary}
	<div
		class="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card py-2 pr-2 pl-4 text-xs"
	>
		{#if overview}
			<span class="text-muted-foreground">
				<span class="font-mono font-semibold text-foreground tabular-nums"
					>{overview.total.toLocaleString()}</span
				> open
			</span>
			<span class="text-muted-foreground">
				<span class="font-mono font-semibold text-foreground tabular-nums"
					>{overview.affected_hosts.toLocaleString()}</span
				>
				{WEB.nounPlural}
			</span>
			<button
				type="button"
				class="text-muted-foreground hover:text-foreground {newOn ? 'underline' : ''}"
				aria-pressed={newOn}
				onclick={onNew}
			>
				<span class="font-mono font-semibold text-info tabular-nums"
					>{overview.new_count.toLocaleString()}</span
				> new
			</button>
			{#if overview.kev_count}
				<button
					type="button"
					class="text-muted-foreground hover:text-foreground {kevOn ? 'underline' : ''}"
					aria-pressed={kevOn}
					onclick={onKev}
				>
					<span class="font-mono font-semibold text-destructive tabular-nums"
						>{overview.kev_count.toLocaleString()}</span
					> known exploited
				</button>
			{/if}
			<span class="flex flex-wrap items-center gap-1">
				{#each SHOWN as sev (sev)}
					{@render sevChip(sev, true)}
				{/each}
			</span>
		{:else}
			<Skeleton class="h-4 w-64" />
		{/if}
		<Button
			variant="ghost"
			size="sm"
			class="ml-auto h-7 gap-1 text-xs text-muted-foreground"
			onclick={() => (findingPrefs.summary = true)}
		>
			<ChevronDown class="size-3.5" /> Summary
		</Button>
	</div>
{:else}
	<div
		class="relative grid gap-x-8 gap-y-4 rounded-xl border bg-card px-4 py-4 lg:grid-cols-[auto_minmax(0,1fr)]"
	>
		<Hint text="Collapse summary">
			{#snippet child(props)}
				<Button
					{...props}
					variant="ghost"
					size="icon"
					class="absolute top-2 right-2 size-7 text-muted-foreground"
					aria-label="Collapse summary"
					onclick={() => (findingPrefs.summary = false)}
				>
					<ChevronUp class="size-4" />
				</Button>
			{/snippet}
		</Hint>
		<div class="flex min-w-0 flex-col gap-4">
			{#if !overview}
				<div class="flex gap-8">
					{#each { length: 4 } as _, i (i)}
						<div class="flex flex-col gap-1.5">
							<Skeleton class="h-3 w-20" />
							<Skeleton class="h-7 w-14" />
						</div>
					{/each}
				</div>
			{:else}
				<div class="flex flex-wrap items-start gap-x-8 gap-y-3">
					<div class="flex flex-col gap-0.5">
						<span class="text-2xs tracking-wide text-muted-foreground uppercase">Open findings</span
						>
						<span class="font-mono text-2xl font-semibold tabular-nums"
							>{overview.total.toLocaleString()}</span
						>
						<span class="text-2xs text-muted-foreground">
							{overview.issues.toLocaleString()}
							{overview.issues === 1 ? 'check' : 'checks'}
						</span>
					</div>
					<div class="flex flex-col gap-0.5">
						<span class="text-2xs tracking-wide text-muted-foreground uppercase"
							>{WEB.nounPlural} affected</span
						>
						<span class="font-mono text-2xl font-semibold tabular-nums"
							>{overview.affected_hosts.toLocaleString()}</span
						>
						{#if tested}
							<span class="text-2xs text-muted-foreground">of {tested.toLocaleString()} tested</span
							>
						{/if}
					</div>
					{@render toggle('New', overview.new_count, newOn, onNew, 'text-info')}
					{@render toggle('Known exploited', overview.kev_count, kevOn, onKev, 'text-destructive')}
				</div>
				<div class="flex flex-col gap-1">
					<span class="text-2xs tracking-wide text-muted-foreground uppercase">
						{unit} by severity
					</span>
					<div class="flex flex-wrap items-center gap-1.5">
						{#each SHOWN as sev (sev)}
							{@render sevChip(sev, false)}
						{/each}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex min-w-0 flex-col gap-1.5">
			<div class="flex items-center justify-between gap-2 pr-8">
				<span class="text-2xs tracking-wide text-muted-foreground uppercase"
					>Most affected {WEB.nounPlural}</span
				>
				<span class="hidden items-center gap-2 text-2xs text-muted-foreground sm:flex">
					{#each BAR as sev (sev)}
						<span class="inline-flex items-center gap-1">
							<span class="size-2 rounded-sm {SEVERITY_CHIP[sev].edge}"></span>{SEVERITY_LABELS[
								sev
							]}
						</span>
					{/each}
				</span>
			</div>
			{#if !overview}
				{#each { length: 4 } as _, i (i)}
					<Skeleton class="h-5 w-full" />
				{/each}
			{:else if hosts.length === 0}
				<span class="py-2 text-xs text-muted-foreground">None</span>
			{:else}
				<ul class="flex flex-col">
					{#each hosts as h (h.host)}
						{@const on = hostOn(h.host)}
						<li>
							<button
								type="button"
								class="group/h grid w-full grid-cols-[minmax(0,1fr)_40%_2rem] sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_2.5rem] items-center gap-3 rounded px-1 py-0.5 text-left hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {on
									? 'bg-muted'
									: ''}"
								aria-pressed={on}
								onclick={() => onHost(h.host)}
							>
								<span class="truncate font-mono text-xs group-hover/h:text-primary">{h.host}</span>
								<Hint
									text={h.counts.map((c) => `${c.count} ${c.label.toLowerCase()}`).join(' · ') ||
										`${h.total} lower severity`}
								>
									{#snippet child(props)}
										<span {...props} class="flex h-2.5 min-w-0 overflow-hidden rounded-sm bg-muted">
											{#each BAR as sev (sev)}
												{@const n = count(h, sev)}
												{#if n}
													<span
														class="h-full {SEVERITY_CHIP[sev].edge}"
														style="width: {(n / max) * 100}%"
													></span>
												{/if}
											{/each}
											<span
												class="h-full bg-muted-foreground/25"
												style="width: {((h.total - BAR.reduce((a, s) => a + count(h, s), 0)) /
													max) *
													100}%"
											></span>
										</span>
									{/snippet}
								</Hint>
								<span class="text-right font-mono text-xs tabular-nums">{h.total}</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</div>
{/if}
