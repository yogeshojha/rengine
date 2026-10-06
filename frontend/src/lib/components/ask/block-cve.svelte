<script lang="ts">
	import Flame from '@lucide/svelte/icons/flame';
	import { Badge } from '$lib/components/ui/badge';
	import EvidenceMark from '$lib/components/evidence-mark.svelte';
	import { SEVERITY_CHIP, severityLabel } from '$lib/config/vulnerabilities';
	import { formatShortDate } from '$lib/utilities/dates';
	import { hostPort } from '$lib/utilities/net';
	import type { CveRecord } from '$lib/types/ask';

	interface Props {
		record: CveRecord;
	}

	let { record }: Props = $props();

	const DESCRIPTION_CLAMP = 'line-clamp-3';

	let epss = $derived(
		record.epss_score == null
			? '—'
			: `${(record.epss_score * 100).toFixed(record.epss_score < 0.1 ? 1 : 0)}%`
	);
	let ladder = $derived(record.ladder.filter((s) => s.count > 0));
	let expanded = $state(false);

	function where(loc: CveRecord['locations'][number]): string {
		const host = loc.host || loc.ip || '';
		return loc.port ? hostPort(host, loc.port) : host;
	}
</script>

<div class="flex flex-col">
	<div class="grid grid-cols-2 divide-border border-b sm:grid-cols-5 sm:divide-x">
		<div class="flex flex-col gap-1 px-4 py-3">
			<span class="text-2xs text-muted-foreground">Severity</span>
			{#if record.severity}
				<span
					class="inline-flex h-5 w-fit items-center rounded px-1.5 text-2xs font-semibold {SEVERITY_CHIP[
						record.severity
					]?.chip ?? 'bg-muted'}">{severityLabel(record.severity)}</span
				>
			{:else}
				<span class="text-sm text-muted-foreground">Not rated</span>
			{/if}
		</div>
		<div class="flex flex-col gap-1 px-4 py-3">
			<span class="text-2xs text-muted-foreground">CVSS</span>
			<span class="text-base leading-5 font-semibold tabular-nums">{record.cvss_score ?? '—'}</span>
		</div>
		<div class="flex flex-col gap-1 px-4 py-3">
			<span class="text-2xs text-muted-foreground">EPSS</span>
			<span class="text-base leading-5 font-semibold tabular-nums">{epss}</span>
		</div>
		<div class="flex flex-col gap-1 px-4 py-3">
			<span class="text-2xs text-muted-foreground">Known exploited</span>
			{#if record.is_kev}
				<Badge variant="destructive" class="w-fit gap-1 px-1.5 text-2xs font-normal">
					<Flame class="size-2.5" />
					{record.kev_date_added ? formatShortDate(record.kev_date_added) : 'KEV'}
				</Badge>
			{:else}
				<span class="text-sm leading-5 text-muted-foreground">Not listed</span>
			{/if}
		</div>
		<div class="flex flex-col gap-1 px-4 py-3">
			<span class="text-2xs text-muted-foreground">Checks in library</span>
			<span class="text-base leading-5 font-semibold tabular-nums">{record.checks}</span>
		</div>
	</div>

	{#if record.description}
		<button
			type="button"
			class="px-4 pt-3 text-left text-sm leading-relaxed text-muted-foreground hover:text-foreground {expanded
				? ''
				: DESCRIPTION_CLAMP}"
			aria-expanded={expanded}
			onclick={() => (expanded = !expanded)}
		>
			{record.description}
		</button>
	{/if}

	<div class="flex flex-col gap-2 px-4 py-3">
		<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
			<span class="text-sm font-medium tabular-nums">
				{record.assets.toLocaleString()}
				{record.assets === 1 ? 'asset' : 'assets'} in scope
			</span>
			{#if record.targets}
				<span class="text-xs text-muted-foreground tabular-nums"
					>on {record.targets} {record.targets === 1 ? 'target' : 'targets'}</span
				>
			{/if}
			{#each ladder as step (step.evidence)}
				<span class="inline-flex items-center gap-1.5 text-xs">
					<EvidenceMark evidence={step.evidence} />
					<span class="font-medium tabular-nums">{step.count}</span>
				</span>
			{/each}
		</div>
		{#if record.locations.length}
			<ul class="flex flex-col divide-y rounded-md border">
				{#each record.locations as loc, i (i)}
					<li class="flex items-center gap-3 px-3 py-1.5">
						<EvidenceMark evidence={loc.evidence} showLabel={false} />
						<span class="min-w-0 flex-1 font-mono text-xs wrap-anywhere">{where(loc)}</span>
						{#if loc.target}
							<span class="text-2xs text-muted-foreground">{loc.target}</span>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
		{#if !record.finding_scans}
			<span class="text-xs text-muted-foreground">No scan in scope ran vulnerability checks.</span>
		{:else if !record.checks && !record.assets}
			<span class="text-xs text-muted-foreground"
				>No check in the library tests for {record.cve}.</span
			>
		{/if}
	</div>
</div>
