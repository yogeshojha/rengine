<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SEVERITY_CHIP, SEVERITY_LABELS, Severity } from '$lib/config/vulnerabilities';
	import { REPORT_STAGE_FILL, REPORT_STAGE_ORDER, formatMonies } from '$lib/config/bounty-reports';
	import { bountyVocabulary } from '$lib/stores/bounty-vocabulary.svelte';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import type { ProgramReports } from '$lib/types/bounty-report';
	import { PCOL } from './columns';

	type Key = 'name' | 'reports' | 'paid' | 'earned' | 'last';

	interface Props {
		programs: ProgramReports[];
		platform: string;
		platformUrl: string;
		query: string;
		onOpen: (handle: string) => void;
	}

	let { programs, platform, platformUrl, query, onOpen }: Props = $props();

	let sortKey = $state<Key>('earned');
	let desc = $state(true);

	const leadCurrency = $derived.by(() => {
		const totals: Record<string, number> = {};
		for (const p of programs)
			for (const m of p.earned) totals[m.currency] = (totals[m.currency] ?? 0) + m.amount;
		let lead: string | null = null;
		for (const [currency, total] of Object.entries(totals))
			if (lead === null || total > totals[lead]) lead = currency;
		return lead;
	});
	const earned = (p: ProgramReports) =>
		p.earned.find((m) => m.currency === leadCurrency)?.amount ?? 0;
	const value: Record<Key, (p: ProgramReports) => number | string> = {
		name: (p) => p.name.toLowerCase(),
		reports: (p) => p.reports,
		paid: (p) => p.paid_reports,
		earned: (p) => earned(p) * 1e6 + p.reports,
		last: (p) => (p.last_submitted_at ? new Date(p.last_submitted_at).getTime() : 0)
	};

	let rows = $derived.by(() => {
		const needle = query.trim().toLowerCase();
		const list = needle
			? programs.filter(
					(p) => p.name.toLowerCase().includes(needle) || p.handle.toLowerCase().includes(needle)
				)
			: programs;
		const get = value[sortKey];
		return [...list].sort((a, b) => {
			const x = get(a);
			const y = get(b);
			const cmp = x < y ? -1 : x > y ? 1 : 0;
			return desc ? -cmp : cmp;
		});
	});

	function sortBy(key: Key) {
		if (sortKey === key) desc = !desc;
		else {
			sortKey = key;
			desc = key !== 'name';
		}
	}

	const href = (p: ProgramReports) =>
		p.in_hub ? ROUTES.bountyHub(p.handle, platform) : `${platformUrl}/${p.handle}`;
</script>

{#snippet head(label: string, key: Key, cls: string)}
	<button
		type="button"
		class="{cls} items-center gap-1 tracking-wide uppercase hover:text-foreground {sortKey === key
			? 'text-foreground'
			: ''}"
		onclick={() => sortBy(key)}
	>
		{label}
		{#if sortKey === key}
			{#if desc}<ArrowDown class="size-3" />{:else}<ArrowUp class="size-3" />{/if}
		{/if}
	</button>
{/snippet}

<ScrollArea orientation="horizontal">
	<div class="w-full min-w-[640px]" role="table" aria-label="Programs">
		<div
			class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
			role="row"
		>
			{@render head('Program', 'name', `${PCOL.program} flex`)}
			{@render head('Reports', 'reports', `${PCOL.outcome} flex`)}
			<div class={PCOL.severity}>Critical · high</div>
			{@render head('Paid', 'paid', PCOL.paid)}
			{@render head('Earned', 'earned', PCOL.earned)}
			{@render head('Last submitted', 'last', PCOL.last)}
			<div class={PCOL.actions}></div>
		</div>
		{#each rows as p (p.handle)}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<div
				class="group flex cursor-pointer items-center gap-3 border-b border-border/60 px-4 py-2.5 hover:bg-muted/30"
				role="row"
				tabindex="-1"
				onclick={() => onOpen(p.handle)}
			>
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div class="{PCOL.program} min-w-0" onclick={(e) => e.stopPropagation()}>
					<a
						href={href(p)}
						target={p.in_hub ? undefined : '_blank'}
						rel={p.in_hub ? undefined : 'noopener noreferrer'}
						class="block truncate text-sm font-medium hover:text-primary">{p.name}</a
					>
					<div class="flex items-center gap-1.5 text-2xs text-muted-foreground">
						<span class="font-mono">@{p.handle}</span>
						{#if !p.in_hub}<span>Not in Bounty Hub</span>{/if}
					</div>
				</div>
				<div class="{PCOL.outcome} flex flex-col gap-1">
					<div class="flex items-baseline justify-between gap-2 text-xs">
						<span class="font-mono font-semibold tabular-nums">{p.reports}</span>
						<span class="flex gap-2 font-mono text-2xs text-muted-foreground tabular-nums">
							{#each REPORT_STAGE_ORDER as stage (stage)}
								{#if p[stage]}
									<Hint text="{p[stage]} {bountyVocabulary.stageLabel(stage).toLowerCase()}">
										{#snippet child(props)}
											<span {...props} class="flex items-center gap-1">
												<span
													class="size-1.5 rounded-full"
													style="background: {REPORT_STAGE_FILL[stage]}"
												></span>
												{p[stage]}
											</span>
										{/snippet}
									</Hint>
								{/if}
							{/each}
						</span>
					</div>
					<div class="flex h-1.5 w-full overflow-hidden rounded-full bg-muted">
						{#each REPORT_STAGE_ORDER as stage (stage)}
							{#if p[stage]}
								<span style="flex: {p[stage]} 1 0; background: {REPORT_STAGE_FILL[stage]}"></span>
							{/if}
						{/each}
					</div>
				</div>
				<div class="{PCOL.severity} items-center gap-1">
					{#each [{ sev: Severity.CRITICAL, n: p.critical }, { sev: Severity.HIGH, n: p.high }] as c (c.sev)}
						{#if c.n}
							<Hint text="{c.n} {SEVERITY_LABELS[c.sev].toLowerCase()}">
								{#snippet child(props)}
									<span
										{...props}
										class="inline-flex h-6 items-center gap-1 rounded-md px-1.5 font-mono text-2xs font-semibold {SEVERITY_CHIP[
											c.sev
										].chip}"
									>
										{c.n}
									</span>
								{/snippet}
							</Hint>
						{/if}
					{/each}
				</div>
				<div class="{PCOL.paid} font-mono text-sm tabular-nums">
					{#if p.paid_reports}{p.paid_reports}{:else}<span class="text-muted-foreground/50">·</span
						>{/if}
				</div>
				<div class="{PCOL.earned} font-mono text-sm font-semibold tabular-nums">
					{#if p.earned.length}{formatMonies(p.earned)}{:else}<span
							class="font-normal text-muted-foreground/50">·</span
						>{/if}
				</div>
				<div class="{PCOL.last} text-xs text-muted-foreground tabular-nums">
					{#if p.last_submitted_at}
						<Hint text={formatShortDate(p.last_submitted_at)}>
							{#snippet child(props)}
								<span {...props}>{relativeTime(p.last_submitted_at)}</span>
							{/snippet}
						</Hint>
					{/if}
				</div>
				<div class={PCOL.actions}>
					<ChevronRight class="size-4 text-muted-foreground group-hover:text-foreground" />
				</div>
			</div>
		{/each}
	</div>
</ScrollArea>
