<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { page } from '$app/state';
	import { untrack } from 'svelte';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Download from '@lucide/svelte/icons/download';
	import Bug from '@lucide/svelte/icons/bug';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Flame from '@lucide/svelte/icons/flame';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import * as Alert from '$lib/components/ui/alert';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CopyButton from '$lib/components/copy-button.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import PanelHead from '$lib/components/panel-head.svelte';
	import SectionHead from '$lib/components/section-head.svelte';
	import Hint from '$lib/components/hint.svelte';
	import PageHeader from '$lib/components/page-header.svelte';
	import LadderStrip from '$lib/components/cve/ladder-strip.svelte';
	import CveLocations from '$lib/components/cve/cve-locations.svelte';
	import ExploitMark from '$lib/components/threat-intel/exploit-mark.svelte';
	import SignalChip from '$lib/components/threat-intel/signal-chip.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import { cvesApi } from '$lib/api/cves';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { BAND_LABELS, epssLabel } from '$lib/config/threat-intel';
	import { nvdUrl } from '$lib/config/software';
	import { formatShortDate, MS_PER_DAY, relativeTimeLong } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { SEVERITY_ORDER } from '$lib/config/vulnerabilities';
	import type { CveExposure, CveIndexRow } from '$lib/types/cve';

	const DESCRIPTION_CLAMP = 280;

	let cve = $derived(decodeURIComponent(page.params.cve ?? '').toUpperCase());
	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let report = $state<CveExposure | null>(null);
	/** what the findings reported, for a CVE the local feeds do not know */
	let reported = $state<CveIndexRow | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let showDescription = $state(false);
	let reqId = 0;

	$effect(() => {
		const id = projectId;
		const wanted = cve;
		if (!id || !wanted) return;
		untrack(() => void load(id, wanted));
	});

	async function load(id: string, wanted: string) {
		const mine = ++reqId;
		loading = true;
		showDescription = false;
		try {
			const data = await cvesApi.exposure(id, wanted);
			if (mine !== reqId) return;
			reported = data.known ? null : await reportedBy(id, wanted);
			if (mine !== reqId) return;
			report = data;
			loadError = null;
		} catch (e) {
			if (mine !== reqId) return;
			loadError = e instanceof Error ? e.message : 'CVE not loaded';
		} finally {
			if (mine === reqId) loading = false;
		}
	}

	async function reportedBy(id: string, wanted: string): Promise<CveIndexRow | null> {
		try {
			const index = await cvesApi.index(id, { q: wanted, size: 5 });
			return index.items.find((row) => row.cve === wanted) ?? null;
		} catch {
			return null;
		}
	}

	let affected = $derived((report?.assets ?? 0) > 0);
	let known = $derived(report?.known ?? true);
	// the worst severity a check reported here, when the feeds have no score of their own
	let locationSeverity = $derived(
		SEVERITY_ORDER.find((sev) => report?.locations.some((loc) => loc.severity === sev)) ?? null
	);
	let severity = $derived(report?.severity ?? reported?.severity ?? locationSeverity);
	let severityFromFindings = $derived(!report?.severity && !!severity);
	let kev = $derived(!!report?.is_kev || (!known && !!reported?.is_kev));
	let ransomware = $derived(!!report?.kev_ransomware || (!known && !!reported?.kev_ransomware));
	let dwellDays = $derived.by(() => {
		if (!report?.first_seen) return null;
		const since = Date.now() - new Date(report.first_seen).getTime();
		return Math.max(0, Math.floor(since / MS_PER_DAY));
	});
	let description = $derived(report?.description?.trim() ?? '');
	let clamped = $derived(description.length > DESCRIPTION_CLAMP && !showDescription);
	let shownDescription = $derived(
		clamped ? `${description.slice(0, DESCRIPTION_CLAMP).trimEnd()}…` : description
	);
	let cvssScore = $derived(report?.cvss_score ?? (known ? null : (reported?.cvss_score ?? null)));
	let cvss = $derived(cvssScore == null ? null : cvssScore.toFixed(1));
	let epssScore = $derived(report?.epss_score ?? (known ? null : (reported?.epss_score ?? null)));
	let epss = $derived(epssScore == null ? null : epssLabel(epssScore));
	let percentile = $derived(
		report?.epss_percentile == null ? null : Math.round(report.epss_percentile * 100)
	);
</script>

<svelte:head><title>{pageTitle(cve || routeLabels.cves)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<a
		href={ROUTES.cves}
		class="inline-flex items-center gap-1.5 self-start text-sm text-muted-foreground hover:text-foreground"
	>
		<ArrowLeft class="size-3.5" />
		{routeLabels.cves}
	</a>

	{#if loading && !report}
		<div class="flex flex-col gap-4">
			<Skeleton class="h-16 max-w-xl" />
			<Skeleton class="h-28" />
			<Skeleton class="h-64" />
		</div>
	{:else if loadError || !report}
		<EmptyState icon={TriangleAlert} title="CVE not loaded" description={loadError ?? undefined}>
			<Button variant="outline" size="sm" onclick={() => void load(projectId, cve)}>Retry</Button>
		</EmptyState>
	{:else}
		{@const shown = report}
		<PageHeader title={report.cve} mono>
			{#snippet titleAside()}
				<CopyButton value={shown.cve} class="size-7" />
				{#if kev}
					<Hint text="On the CISA Known Exploited Vulnerabilities list">
						{#snippet child(props)}
							<span {...props} class="flex h-5 items-center">
								<Badge variant="destructive" class="gap-1 px-1.5 text-2xs font-normal">
									<Flame class="size-2.5" /> Known exploited
								</Badge>
							</span>
						{/snippet}
					</Hint>
				{/if}
				{#if ransomware}
					<Badge variant="destructive" class="px-1.5 text-2xs font-normal">Ransomware</Badge>
				{/if}
			{/snippet}
			{#snippet actions()}
				<Button
					variant="outline"
					size="sm"
					href={nvdUrl(shown.cve)}
					target="_blank"
					rel="noopener noreferrer"
				>
					<ExternalLink class="size-3.5" />
					Open on NVD
				</Button>
			{/snippet}
			<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
				{#if severity}
					<SeverityMark {severity} />
					{#if severityFromFindings}<span>reported by findings</span>{/if}
				{:else}
					<span>Not scored by NVD</span>
				{/if}
				{#if cvss}
					<Hint text={report.cvss_vector ?? 'CVSS base score'}>
						{#snippet child(props)}
							<span {...props} class="font-mono tabular-nums">CVSS {cvss}</span>
						{/snippet}
					</Hint>
				{/if}
				{#if report.published_at}
					<span>Published {formatShortDate(report.published_at)}</span>
				{/if}
				{#if !report.known}
					<span>Not in the local NVD corpus</span>
				{/if}
			</div>
			{#if description}
				<p class="max-w-3xl text-sm text-muted-foreground">
					{shownDescription}
					{#if description.length > DESCRIPTION_CLAMP}
						<button
							type="button"
							class="ml-1 text-xs text-foreground hover:text-primary"
							onclick={() => (showDescription = !showDescription)}
						>
							{showDescription ? 'Show less' : 'Show more'}
						</button>
					{/if}
				</p>
			{/if}
		</PageHeader>

		{#if !report.corpus_ready}
			<Alert.Alert>
				<Alert.AlertTitle>Software inference not available</Alert.AlertTitle>
				<Alert.AlertDescription>
					The NVD corpus is not loaded. Only findings a check reported are counted.
				</Alert.AlertDescription>
			</Alert.Alert>
		{/if}

		<Card.Root class="gap-0 overflow-hidden py-0">
			<div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 border-b px-5 py-4">
				<div class="flex min-w-0 flex-col gap-1">
					{#if affected}
						<span class="text-lg leading-6 font-semibold">
							{plural(report.assets, 'asset', 'assets')} across {plural(
								report.targets,
								'target',
								'targets'
							)}
						</span>
						{#if report.first_seen && dwellDays != null}
							<span class="text-xs text-muted-foreground">
								{#if dwellDays === 0}
									First seen today
								{:else}
									First seen {formatShortDate(report.first_seen)} · exposed for {plural(
										dwellDays,
										'day',
										'days'
									)}
								{/if}
							</span>
						{/if}
					{:else}
						<span class="text-lg leading-6 font-semibold">No asset carries this CVE</span>
						<span class="text-xs text-muted-foreground">
							{#if report.corpus_ready}{plural(report.software_scans, 'target', 'targets')} with software
								inference ·
							{/if}{plural(report.finding_scans, 'target', 'targets')} with checks
						</span>
					{/if}
				</div>
				{#if report.suppressed}
					<span class="text-xs text-muted-foreground">
						{plural(report.suppressed, 'finding', 'findings')} set aside by a reviewer, not counted
					</span>
				{/if}
			</div>
			<LadderStrip cve={report.cve} ladder={report.ladder} />
		</Card.Root>

		<div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
			<div class="flex min-w-0 flex-col gap-6">
				{#if report.locations.length}
					<Card.Root class="gap-0 overflow-hidden py-0">
						<PanelHead title="Locations">
							{report.locations_total.toLocaleString()}
						</PanelHead>
						<CveLocations
							cve={report.cve}
							locations={report.locations}
							total={report.locations_total}
						/>
					</Card.Root>
				{:else}
					<EmptyState
						compact
						icon={Bug}
						title="No locations"
						description={report.finding_scans === 0 && report.software_scans === 0
							? 'Not scanned'
							: 'No version implies it and no check reported it.'}
					/>
				{/if}
			</div>

			<aside class="flex min-w-0 flex-col gap-6">
				<Card.Root class="gap-0 overflow-hidden py-0">
					<PanelHead title="Exploitation" />
					<div class="flex flex-col gap-4 px-5 py-4">
						{#if known}
							<div class="flex items-center gap-3">
								<ExploitMark score={report.exploit_score} size={44} />
								<span class="text-sm font-medium">Rank {report.exploit_score} of 100</span>
							</div>
						{:else}
							<div class="flex flex-col items-start gap-1.5">
								<span class="text-sm font-medium">Unknown</span>
								<span class="text-xs text-muted-foreground">
									The threat-intel feeds are not downloaded, so this CVE has no exploitation rank.
									Values below are what the findings reported.
								</span>
								<Button variant="outline" size="sm" href={ROUTES.arsenal('threat-intel')}>
									<Download class="size-3.5" />
									Download feeds in Arsenal
								</Button>
							</div>
						{/if}
						{#if report.intel_kinds.length}
							<div class="flex flex-wrap gap-1">
								{#each report.intel_kinds as kind (kind)}
									<SignalChip {kind} />
								{/each}
							</div>
						{/if}
						<dl class="flex flex-col divide-y divide-border/60 text-sm">
							<div class="flex items-baseline justify-between gap-3 py-2">
								<dt class="text-xs text-muted-foreground">EPSS</dt>
								<dd class="text-right tabular-nums">
									{#if epss != null}
										{epss}
										{#if report.band}
											<span class="text-xs text-muted-foreground">
												· {BAND_LABELS[report.band] ?? report.band}
											</span>
										{/if}
									{:else}
										<span class="text-xs text-muted-foreground"
											>{known ? 'Not scored' : 'Unknown'}</span
										>
									{/if}
								</dd>
							</div>
							{#if percentile != null}
								<div class="flex items-baseline justify-between gap-3 py-2">
									<dt class="text-xs text-muted-foreground">Percentile</dt>
									<dd class="tabular-nums">{percentile}</dd>
								</div>
							{/if}
							<div class="flex items-baseline justify-between gap-3 py-2">
								<dt class="text-xs text-muted-foreground">CISA KEV</dt>
								<dd class="text-right">
									{#if kev}
										{#if report.kev_date_added}Added {formatShortDate(
												report.kev_date_added
											)}{:else}Listed{/if}
									{:else}
										<span class="text-xs text-muted-foreground"
											>{known ? 'Not listed' : 'Unknown'}</span
										>
									{/if}
								</dd>
							</div>
							{#if report.kev_due_date}
								<div class="flex items-baseline justify-between gap-3 py-2">
									<dt class="text-xs text-muted-foreground">Patch due</dt>
									<dd class="tabular-nums">{formatShortDate(report.kev_due_date)}</dd>
								</div>
							{/if}
							{#if report.last_modified_at}
								<div class="flex items-baseline justify-between gap-3 py-2">
									<dt class="text-xs text-muted-foreground">NVD updated</dt>
									<dd class="text-xs">{relativeTimeLong(report.last_modified_at)}</dd>
								</div>
							{/if}
						</dl>
						{#if report.kev_required_action}
							<div class="flex flex-col gap-1">
								<SectionHead title="Required action" />
								<p class="text-xs text-muted-foreground">{report.kev_required_action}</p>
							</div>
						{/if}
					</div>
				</Card.Root>

				{#if report.by_target.length}
					<Card.Root class="gap-0 overflow-hidden py-0">
						<PanelHead title="By target">
							{plural(report.by_target.length, 'target', 'targets')}
						</PanelHead>
						<ul class="divide-y divide-border/60">
							{#each report.by_target as row (row.target_id)}
								<li>
									<a
										href={ROUTES.target(row.target_id)}
										class="flex items-start justify-between gap-3 px-5 py-2.5 text-sm hover:bg-accent/40"
									>
										<span class="flex min-w-0 flex-col gap-0.5">
											<span class="truncate font-mono text-xs leading-5">{row.target_value}</span>
											{#if row.first_seen}
												<span class="text-2xs text-muted-foreground">
													First seen {formatShortDate(row.first_seen)}
												</span>
											{/if}
										</span>
										<span class="flex shrink-0 flex-col items-end gap-0.5 text-right">
											<span class="text-xs leading-5 tabular-nums">
												{plural(row.assets, 'asset', 'assets')}
											</span>
											<span class="text-2xs text-muted-foreground tabular-nums">
												{#if row.software}{row.software} inferred{/if}
												{#if row.software && row.findings}·{/if}
												{#if row.findings}{plural(row.findings, 'finding')}{/if}
											</span>
										</span>
									</a>
								</li>
							{/each}
						</ul>
					</Card.Root>
				{/if}
			</aside>
		</div>
	{/if}
</div>
