<script lang="ts">
	import Flame from '@lucide/svelte/icons/flame';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import Hint from '$lib/components/hint.svelte';
	import Widget from './widget.svelte';
	import RankedBars, { type BarRow } from './ranked-bars.svelte';
	import SeverityBar from '$lib/components/scans/results/vulnerabilities/severity-bar.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { SEVERITY_FILL, SEVERITY_LABELS, severityRank } from '$lib/config/vulnerabilities';
	import { exactToken } from '$lib/utilities/scan-insights';
	import { epssPercent } from '$lib/utilities/vulns';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		windowText,
		type DashboardOverview,
		type DashboardWindow,
		type QueueFilter
	} from '$lib/types/dashboard';

	interface Props {
		overview: DashboardOverview;
		window: DashboardWindow;
		filter: QueueFilter;
		onFilter: (f: QueueFilter) => void;
		class?: string;
	}

	let { overview, window, filter, onFilter, class: className = '' }: Props = $props();

	const SHOWN = 8;
	const TOP_TARGETS = 6;
	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];
	const plural = (n: number, one: string, many: string) =>
		`${n.toLocaleString()} ${n === 1 ? one : many}`;

	let expanded = $state(false);
	let risk = $derived(overview.risk);
	let queue = $derived(risk.queue);
	let filters = $derived.by<{ key: QueueFilter; label: string; count: number }[]>(() => {
		const sev = (key: string) => risk.by_severity.find((s) => s.severity === key)?.count ?? 0;
		const out: { key: QueueFilter; label: string; count: number }[] = [
			{ key: 'all', label: 'All', count: risk.total }
		];
		if (risk.kev > 0) out.push({ key: 'kev', label: 'Known exploited', count: risk.kev });
		if (sev('critical') > 0)
			out.push({ key: 'critical', label: 'Critical', count: sev('critical') });
		if (sev('high') > 0) out.push({ key: 'high', label: 'High', count: sev('high') });
		const fresh = queue.filter((f) => f.is_new).length;
		if (fresh > 0) out.push({ key: 'new', label: 'New', count: fresh });
		return out;
	});
	let active = $derived(filters.some((f) => f.key === filter) ? filter : 'all');
	let filtered = $derived(
		queue.filter((f) => {
			switch (active) {
				case 'kev':
					return f.is_kev;
				case 'critical':
					return f.severity === 'critical';
				case 'high':
					return f.severity === 'high';
				case 'new':
					return f.is_new;
				default:
					return true;
			}
		})
	);
	let shown = $derived(expanded ? filtered : filtered.slice(0, SHOWN));
	let hidden = $derived(filtered.length - shown.length);

	let concentration = $derived<BarRow[]>(
		overview.targets
			.filter((t) => t.findings > 0 && t.risk_scan_id)
			.sort(
				(a, b) =>
					b.kev - a.kev ||
					severityRank(a.worst_severity) - severityRank(b.worst_severity) ||
					b.actionable - a.actionable ||
					b.findings - a.findings
			)
			.slice(0, TOP_TARGETS)
			.map((t) => ({
				key: t.id,
				label: t.value,
				count: t.findings,
				mono: true,
				sub: t.kev ? `${t.kev} KEV` : (SEVERITY_LABELS[t.worst_severity ?? ''] ?? undefined),
				tone: t.worst_severity ? SEVERITY_FILL[t.worst_severity] : 'var(--series)',
				href: t.risk_scan_id ? ROUTES.scanTab(t.risk_scan_id, VULNS.tab) : undefined
			}))
	);

	const href = (scanId: string, q: string) =>
		ROUTES.scanTab(scanId, VULNS.tab, { [VULNS.queryParam]: q });
</script>

<Widget
	title="Findings by risk"
	description="Open findings, ranked by exploitability"
	href={ROUTES.surface(VULNS.tab)}
	hrefLabel="All findings"
	class={className}
>
	{#snippet head()}
		<span class="tabular-nums">
			{risk.targets_affected} of {plural(risk.targets_scanned, 'scanned target', 'scanned targets')} affected
		</span>
	{/snippet}
	{#if risk.total === 0}
		<div class="flex items-center gap-3 px-5 py-8 text-sm text-muted-foreground">
			<ShieldCheck class="size-5 text-success" />
			No open findings on {plural(risk.targets_scanned, 'scanned target', 'scanned targets')}.
		</div>
	{:else}
		<div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_15rem]">
			<div class="flex min-w-0 flex-col">
				<div class="flex flex-col gap-3 border-b px-5 py-3">
					<SeverityBar counts={risk.by_severity} />
					<div class="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
						<div class="flex flex-wrap gap-x-4 gap-y-1">
							{#each risk.by_severity.filter((s) => s.count > 0) as part (part.severity)}
								<a
									href={ROUTES.surface(VULNS.tab, {
										[VULNS.queryParam]: `severity:${part.severity}`
									})}
									class="flex items-center gap-1.5 text-xs hover:underline"
								>
									<span
										class="size-2 shrink-0 rounded-full"
										style="background:{SEVERITY_FILL[part.severity]}"
									></span>
									<span class="text-muted-foreground">{SEVERITY_LABELS[part.severity]}</span>
									<span class="font-medium tabular-nums">{part.count.toLocaleString()}</span>
								</a>
							{/each}
						</div>
						{#if filters.length > 1}
							<ToggleGroup.Root
								type="single"
								variant="outline"
								size="sm"
								value={active}
								onValueChange={(v) => v && onFilter(v as QueueFilter)}
								aria-label="Filter findings"
							>
								{#each filters as f (f.key)}
									<ToggleGroup.Item value={f.key} class="gap-1.5 px-2.5 text-xs">
										{f.label}
										<span class="text-muted-foreground tabular-nums"
											>{f.count.toLocaleString()}</span
										>
									</ToggleGroup.Item>
								{/each}
							</ToggleGroup.Root>
						{/if}
					</div>
				</div>
				<ul class="divide-y divide-border/60">
					{#each shown as f (f.id)}
						<li>
							<a
								href={href(f.scan_id, exactToken('template', f.template_id))}
								class="flex items-center gap-3 px-5 py-2 transition-colors hover:bg-muted/40"
							>
								<SeverityMark severity={f.severity} size="sm" />
								<span class="flex min-w-0 flex-1 flex-col">
									<span class="flex min-w-0 items-center gap-2">
										<span class="truncate text-sm font-medium">{f.name}</span>
										{#if f.is_kev}
											<Badge variant="destructive" class="h-4 gap-1 px-1.5 text-2xs">
												<Flame class="size-2.5" /> KEV
											</Badge>
										{/if}
										{#if f.is_new}
											<Badge variant="info" class="h-4 px-1.5 text-2xs">New</Badge>
										{/if}
									</span>
									<span class="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
										<span class="truncate font-mono">{f.host ?? f.matched_at}</span>
										{#if f.host_count > 1}
											<span class="shrink-0">· on {f.host_count} web assets</span>
										{/if}
										<span class="shrink-0">· {f.target_value}</span>
									</span>
								</span>
								{#if f.epss_score !== null}
									<Hint text="EPSS: probability of exploitation within 30 days">
										{#snippet child(props)}
											<span {...props} class="shrink-0 text-xs tabular-nums text-muted-foreground">
												{epssPercent(f.epss_score)}
											</span>
										{/snippet}
									</Hint>
								{/if}
								<span class="hidden shrink-0 text-xs text-muted-foreground sm:inline">
									{relativeTime(f.discovered_at)}
								</span>
							</a>
						</li>
					{/each}
				</ul>
				{#if hidden > 0 || expanded}
					<div class="px-5 py-2">
						<Button
							variant="ghost"
							size="sm"
							class="h-7 gap-1 px-2 text-xs"
							onclick={() => (expanded = !expanded)}
						>
							<ChevronDown class="size-3.5 transition-transform {expanded ? 'rotate-180' : ''}" />
							{expanded ? 'Show fewer' : `Show ${hidden} more`}
						</Button>
					</div>
				{/if}
			</div>
			{#if concentration.length}
				<div class="flex flex-col gap-2 border-t px-5 py-4 lg:border-t-0 lg:border-l">
					<span class="text-2xs font-medium tracking-wider text-muted-foreground uppercase">
						Findings by target
					</span>
					<RankedBars rows={concentration} dense />
				</div>
			{/if}
		</div>
	{/if}
	{#snippet footer()}
		{#if risk.new_in_window > 0}
			<a
				href={ROUTES.surface(VULNS.tab, { [VULNS.queryParam]: 'is:new' })}
				class="font-medium text-success hover:underline"
			>
				▲ {plural(risk.new_in_window, 'finding', 'findings')} first reported in the {windowText(
					window
				)}
			</a>
		{:else}
			No new findings in the {windowText(window)}
		{/if}
		{#if risk.suppressed > 0}
			<span> · {risk.suppressed} suppressed by triage</span>
		{/if}
	{/snippet}
</Widget>
