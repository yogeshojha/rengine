<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Filter from '@lucide/svelte/icons/filter';
	import Award from '@lucide/svelte/icons/award';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SEVERITY_CHIP, SEVERITY_LABELS } from '$lib/config/vulnerabilities';
	import {
		REPORT_SEVERITY_KEY,
		REPORT_STAGE_FILL,
		formatMonies,
		formatMoney
	} from '$lib/config/bounty-reports';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import { ReportStage, type BountyReport, type ProgramReports } from '$lib/types/bounty-report';
	import { RCOL } from './columns';

	interface Props {
		report: BountyReport;
		program?: ProgramReports;
		platformLabel: string;
		platformUrl: string;
		expanded: boolean;
		focused: boolean;
		compact: boolean;
		onToggle: () => void;
		onProgram: (handle: string) => void;
		onSearch: (text: string) => void;
	}

	let {
		report,
		program,
		platformLabel,
		platformUrl,
		expanded,
		focused,
		compact,
		onToggle,
		onProgram,
		onSearch
	}: Props = $props();

	let sev = $derived(report.severity ? (REPORT_SEVERITY_KEY[report.severity] ?? null) : null);
	let programName = $derived(report.program_name ?? report.program_handle ?? '');
	let programHref = $derived(
		report.program_handle
			? report.program_in_hub
				? ROUTES.bountyHub(report.program_handle, report.platform)
				: `${platformUrl}/${report.program_handle}`
			: null
	);

	let steps = $derived(
		[
			{ label: 'Submitted', at: report.submitted_at, tone: 'var(--foreground)' },
			{ label: 'Triaged', at: report.triaged_at, tone: 'var(--info)' },
			...report.awards.map((a) => ({
				label: `Bounty ${formatMoney(a.amount, a.currency)}${a.bonus ? ` · bonus ${formatMoney(a.bonus, a.currency)}` : ''}`,
				at: a.awarded_at,
				tone: 'var(--series)'
			})),
			{
				label: report.stage === ReportStage.Open ? '' : report.state_label,
				at: report.closed_at,
				tone: REPORT_STAGE_FILL[report.stage]
			},
			{ label: 'Disclosed', at: report.disclosed_at, tone: 'var(--muted-foreground)' }
		]
			.filter((s) => s.at && s.label)
			.sort((a, b) => new Date(a.at!).getTime() - new Date(b.at!).getTime())
	);
</script>

<div
	id="report-row-{report.id}"
	class="group relative border-b border-border/60 transition-colors {expanded
		? 'bg-muted/25'
		: focused
			? 'bg-muted/30'
			: ''}"
>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="flex cursor-pointer items-center gap-3 px-4 {compact
			? 'py-1.5'
			: 'py-2.5'} hover:bg-muted/30"
		role="row"
		tabindex="-1"
		onclick={onToggle}
	>
		<div class={RCOL.report}>
			<div class="flex min-w-0 items-center gap-1.5">
				<span class="truncate text-sm font-medium">{report.title}</span>
			</div>
			<div
				class="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-2xs text-muted-foreground"
			>
				<span class="font-mono">#{report.external_id}</span>
				{#if report.weakness}
					<span class="truncate">{report.weakness}</span>
				{/if}
				{#if report.asset_identifier}
					<span class="truncate font-mono">{report.asset_identifier}</span>
				{/if}
				<span class="truncate md:hidden">{programName}</span>
			</div>
		</div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class={RCOL.program} onclick={(e) => e.stopPropagation()}>
			{#if programHref}
				<a
					href={programHref}
					target={report.program_in_hub ? undefined : '_blank'}
					rel={report.program_in_hub ? undefined : 'noopener noreferrer'}
					class="block truncate text-sm hover:text-primary"
				>
					{programName}
				</a>
				<button
					type="button"
					class="flex max-w-full items-center gap-1 truncate font-mono text-2xs text-muted-foreground hover:text-foreground"
					aria-label="Filter to {programName}"
					onclick={() => onProgram(report.program_handle!)}
				>
					@{report.program_handle}
					<Filter class="size-2.5 opacity-0 group-hover:opacity-100" />
				</button>
			{/if}
		</div>
		<div class={RCOL.severity}>
			{#if sev}
				<span
					class="inline-flex h-6 items-center gap-1 rounded-md px-1.5 font-mono text-2xs font-semibold {SEVERITY_CHIP[
						sev
					].chip}"
				>
					{SEVERITY_LABELS[sev]}
					{#if report.severity_score != null}<span class="opacity-70"
							>{report.severity_score.toFixed(1)}</span
						>{/if}
				</span>
			{:else}
				<span class="text-xs text-muted-foreground">Not rated</span>
			{/if}
		</div>
		<div class={RCOL.state}>
			<div class="flex items-center gap-1.5 text-sm">
				<span class="flex h-5 items-center">
					<span class="size-1.5 rounded-full" style="background: {REPORT_STAGE_FILL[report.stage]}"
					></span>
				</span>
				{report.state_label}
			</div>
			{#if report.closed_at}
				<div class="pl-3 text-2xs text-muted-foreground">
					{formatShortDate(report.closed_at)}
				</div>
			{/if}
		</div>
		<div class="{RCOL.bounty} font-mono text-sm tabular-nums">
			{#if report.awarded.length}
				<span class="font-semibold">{formatMonies(report.awarded)}</span>
			{:else}
				<span class="text-muted-foreground/50">·</span>
			{/if}
		</div>
		<div class="{RCOL.submitted} text-xs text-muted-foreground tabular-nums">
			{#if report.submitted_at}
				<Hint text={formatShortDate(report.submitted_at)}>
					{#snippet child(props)}
						<span {...props}>{relativeTime(report.submitted_at)}</span>
					{/snippet}
				</Hint>
			{/if}
		</div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="{RCOL.actions} items-center gap-0.5" onclick={(e) => e.stopPropagation()}>
			<Button
				variant="ghost"
				size="icon"
				class="size-7"
				aria-label={expanded ? 'Collapse report' : 'Expand report'}
				aria-expanded={expanded}
				onclick={onToggle}
			>
				<ChevronDown class="size-4 transition-transform {expanded ? 'rotate-180' : ''}" />
			</Button>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							size="icon"
							class="size-7"
							aria-label="Report actions"
						>
							<Ellipsis class="size-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-56">
					<DropdownMenu.Item onSelect={() => window.open(report.url, '_blank', 'noopener')}>
						<ExternalLink /> Open on {platformLabel}
					</DropdownMenu.Item>
					{#if report.program_handle}
						{#if report.program_in_hub}
							<DropdownMenu.Item onSelect={() => programHref && goto(programHref)}>
								<Award /> Open program
							</DropdownMenu.Item>
						{/if}
						<DropdownMenu.Item onSelect={() => onProgram(report.program_handle!)}>
							<Filter /> Filter to this program
						</DropdownMenu.Item>
					{/if}
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>

	{#if expanded}
		<div
			class="grid gap-3 px-4 pt-1 pb-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)]"
		>
			<section class="rounded-md border bg-card p-3">
				<h4 class="mb-2 text-2xs tracking-wide text-muted-foreground uppercase">Timeline</h4>
				<ol class="flex flex-col">
					{#each steps as s, i (i)}
						<li class="relative flex gap-3 pb-2.5 last:pb-0">
							{#if i < steps.length - 1}
								<span class="absolute top-4 bottom-0 left-[3px] w-px bg-border" aria-hidden="true"
								></span>
							{/if}
							<span class="flex h-5 items-center">
								<span class="size-[7px] rounded-full" style="background: {s.tone}"></span>
							</span>
							<span class="flex min-w-0 flex-1 items-baseline justify-between gap-3 text-sm">
								<span class="truncate">{s.label}</span>
								<span class="shrink-0 font-mono text-2xs text-muted-foreground">
									{formatShortDate(s.at!)}
								</span>
							</span>
						</li>
					{/each}
				</ol>
				{#if report.last_program_activity_at}
					<p class="mt-2 border-t pt-2 text-2xs text-muted-foreground">
						Last program activity {relativeTime(report.last_program_activity_at)}
					</p>
				{/if}
			</section>

			<section class="flex flex-col gap-2 rounded-md border bg-card p-3">
				<h4 class="text-2xs tracking-wide text-muted-foreground uppercase">Program</h4>
				{#if report.program_handle}
					<div class="flex min-w-0 flex-col">
						{#if programHref}
							<a
								href={programHref}
								target={report.program_in_hub ? undefined : '_blank'}
								rel={report.program_in_hub ? undefined : 'noopener noreferrer'}
								class="truncate text-sm font-medium hover:text-primary">{programName}</a
							>
						{/if}
						<span class="font-mono text-2xs text-muted-foreground">@{report.program_handle}</span>
					</div>
					{#if program}
						<dl class="grid grid-cols-3 gap-2 text-center">
							{#each [{ k: 'Reports', v: String(program.reports) }, { k: 'Resolved', v: String(program.resolved) }, { k: 'Earned', v: program.earned.length ? formatMonies(program.earned) : '0' }] as cell (cell.k)}
								<div class="rounded-md bg-muted/30 px-1 py-1.5">
									<dt class="text-2xs text-muted-foreground">{cell.k}</dt>
									<dd class="font-mono text-sm font-semibold tabular-nums">{cell.v}</dd>
								</div>
							{/each}
						</dl>
					{/if}
					<div class="mt-auto flex flex-wrap gap-2">
						<Button
							size="sm"
							variant="outline"
							class="h-7 gap-1.5 text-xs"
							onclick={() => onProgram(report.program_handle!)}
						>
							<Filter class="size-3" /> Filter to this program
						</Button>
						{#if report.program_in_hub && programHref}
							<Button size="sm" variant="outline" class="h-7 gap-1.5 text-xs" href={programHref}>
								<Award class="size-3" /> Open program
							</Button>
						{/if}
					</div>
				{:else}
					<span class="text-sm text-muted-foreground">No program</span>
				{/if}
			</section>

			<section class="flex flex-col gap-2 rounded-md border bg-card p-3">
				<h4 class="text-2xs tracking-wide text-muted-foreground uppercase">Finding</h4>
				<dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
					{#if report.weakness}
						<dt class="text-muted-foreground">Weakness</dt>
						<dd class="min-w-0">
							<button
								type="button"
								class="truncate text-left hover:text-primary"
								onclick={() => onSearch(report.weakness!)}>{report.weakness}</button
							>
						</dd>
					{/if}
					{#if report.asset_identifier}
						<dt class="text-muted-foreground">Asset</dt>
						<dd class="flex min-w-0 items-center gap-1">
							<button
								type="button"
								class="truncate text-left font-mono text-xs hover:text-primary"
								onclick={() => onSearch(report.asset_identifier!)}>{report.asset_identifier}</button
							>
							<CopyButton value={report.asset_identifier} class="shrink-0" />
						</dd>
					{/if}
					{#if sev}
						<dt class="text-muted-foreground">Severity</dt>
						<dd>
							{SEVERITY_LABELS[sev]}{report.severity_score != null
								? ` · ${report.severity_score.toFixed(1)}`
								: ''}
						</dd>
					{/if}
				</dl>
				<div class="mt-auto">
					<Button
						size="sm"
						class="h-7 gap-1.5 text-xs"
						href={report.url}
						target="_blank"
						rel="noopener noreferrer"
					>
						<ExternalLink class="size-3" /> Open on {platformLabel}
					</Button>
				</div>
			</section>
		</div>
	{/if}
</div>
