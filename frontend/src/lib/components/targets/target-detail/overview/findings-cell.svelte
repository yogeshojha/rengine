<script lang="ts">
	import { goto } from '$app/navigation';
	import Cell from '$lib/components/cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import SeverityBar from '$lib/components/scans/results/vulnerabilities/severity-bar.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { SEVERITY_FILL, severityLabel } from '$lib/config/vulnerabilities';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { RankedFinding, ScanVulnerabilities } from '$lib/utilities/vulns';
	import type { TargetRisk } from '$lib/types/target-summary';

	interface Props {
		risk: TargetRisk;
		vulns: ScanVulnerabilities | null;
		scanId: string;
		loading?: boolean;
		class?: string;
	}

	let { risk, vulns, scanId, loading = false, class: className = '' }: Props = $props();

	const TOP = 5;
	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];
	const link = (q?: string) =>
		ROUTES.scanTab(scanId, VULN.tab, q ? { [VULN.queryParam]: q } : undefined);

	let counts = $derived(vulns?.by_severity ?? risk.by_severity);
	let legend = $derived(counts.filter((c) => c.count > 0));
	let total = $derived(vulns?.total ?? risk.total);
	let kev = $derived(vulns?.kev_count ?? risk.kev);
	let actionable = $derived(vulns?.actionable ?? risk.actionable);
	let newCount = $derived(vulns?.new_count ?? 0);
	let suppressed = $derived(vulns?.suppressed ?? risk.suppressed);
	let top = $derived((vulns?.top_findings ?? []).slice(0, TOP));

	const id = (f: RankedFinding) => f.cve_ids[0] ?? f.template_id;
	const epss = (f: RankedFinding) =>
		f.epss_score === null ? null : Math.round(f.epss_score * 100);
	const findingHref = (f: RankedFinding) => link(`template="${f.template_id}"`);

	interface Stat {
		key: string;
		label: string;
		value: number;
		query: string;
		tone?: string;
	}
	let stats = $derived<Stat[]>(
		[
			{
				key: 'kev',
				label: 'Known exploited',
				value: kev,
				query: 'is:kev',
				tone: 'text-destructive'
			},
			{
				key: 'actionable',
				label: 'Actionable',
				value: actionable,
				query: 'severity:critical or severity:high or severity:medium'
			},
			{ key: 'new', label: 'New this run', value: newCount, query: 'is:new' }
		].filter((s) => s.value > 0)
	);
</script>

<Cell
	id="findings"
	title="Findings"
	description={risk.observed_at ? `From the ${formatShortDate(risk.observed_at)} run` : undefined}
	href={link()}
	hrefLabel="{total.toLocaleString()} open"
	loading={loading && !total}
	class={className}
>
	{#if total > 0}
		<SeverityBar {counts} height="h-2.5" onPick={(s) => goto(link(`severity:${s}`))} />
		<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
			{#each legend as c (c.severity)}
				<a
					href={link(`severity:${c.severity}`)}
					class="flex items-center gap-1.5 hover:text-foreground"
				>
					<span class="size-2.5 rounded-[2px]" style="background:{SEVERITY_FILL[c.severity]}"
					></span>
					{c.label}
					<span class="font-medium text-foreground tabular-nums">{c.count.toLocaleString()}</span>
				</a>
			{/each}
		</div>
		{#if stats.length}
			<div class="grid grid-cols-3 gap-2">
				{#each stats as s (s.key)}
					<a
						href={link(s.query)}
						class="flex flex-col gap-0.5 rounded-lg border bg-muted/20 px-2.5 py-2 transition-colors hover:bg-muted/50"
					>
						<span class="text-2xs text-muted-foreground">{s.label}</span>
						<span
							class="text-lg leading-none font-semibold tracking-tight tabular-nums {s.tone ?? ''}"
						>
							{s.value.toLocaleString()}
						</span>
					</a>
				{/each}
			</div>
		{/if}
		{#if top.length}
			<ul class="flex flex-col">
				{#each top as f (f.id)}
					<li class="border-t first:border-t-0">
						<a
							href={findingHref(f)}
							class="-mx-2 grid grid-cols-[auto_minmax(0,1fr)_auto] items-start gap-x-2.5 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted/40"
						>
							<span class="flex h-5 items-center">
								<span
									class="size-2 rounded-full"
									style="background:{SEVERITY_FILL[f.severity] ?? 'var(--sev-info)'}"
								></span>
							</span>
							<span class="flex min-w-0 flex-col">
								<span class="flex min-w-0 items-center gap-2">
									<Hint text={f.name}>
										{#snippet child(props)}
											<span {...props} class="truncate font-medium">{f.name}</span>
										{/snippet}
									</Hint>
									{#if f.is_kev}
										<Badge variant="destructive" class="px-1.5 py-0 text-2xs">KEV</Badge>
									{:else if f.is_new}
										<Badge variant="info" class="px-1.5 py-0 text-2xs">New</Badge>
									{/if}
								</span>
								<span
									class="flex min-w-0 flex-wrap items-center gap-x-2 text-2xs text-muted-foreground"
								>
									<span class="font-mono">{id(f)}</span>
									<span>{severityLabel(f.severity)}</span>
									{#if f.host}<span class="truncate font-mono">{f.host}</span>{/if}
									{#if f.host_count > 1}<span class="tabular-nums">{f.host_count} web assets</span
										>{/if}
								</span>
							</span>
							{#if epss(f) !== null}
								<Hint text="EPSS {epss(f)}%">
									{#snippet child(props)}
										<span {...props} class="flex h-5 items-center gap-1.5 text-2xs tabular-nums">
											{epss(f)}%
											<span class="h-1 w-10 overflow-hidden rounded-full bg-muted">
												<span class="block h-full bg-series" style="width:{epss(f)}%"></span>
											</span>
										</span>
									{/snippet}
								</Hint>
							{/if}
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	{:else}
		<span class="text-sm text-muted-foreground">No finding</span>
	{/if}
	{#snippet footer()}
		{#if vulns}
			<span>
				{vulns.affected_hosts.toLocaleString()} of {vulns.scanned_hosts.toLocaleString()} web assets affected{#if suppressed}
					· {suppressed.toLocaleString()} suppressed{/if}
			</span>
		{:else if suppressed}
			<span>{suppressed.toLocaleString()} suppressed</span>
		{/if}
	{/snippet}
</Cell>
