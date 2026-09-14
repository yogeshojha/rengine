<script lang="ts">
	import Cell from './cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { QueueTier, TIER_HELP, TIER_LABELS, TIER_ORDER } from '$lib/config/dashboard';
	import { SEVERITY_FILL, severityLabel } from '$lib/config/vulnerabilities';
	import { evidenceLabel } from '$lib/config/evidence';
	import { relativeTime } from '$lib/utilities/dates';
	import type { DashboardFinding, DashboardRisk } from '$lib/types/dashboard';

	interface Props {
		risk: DashboardRisk;
		class?: string;
	}

	let { risk, class: className = '' }: Props = $props();

	const PER_COLUMN = 3;
	const VULN = SURFACE[SurfaceDimension.VULNERABILITIES];
	const TIER_QUERY: Record<QueueTier, string> = {
		[QueueTier.Act]: 'is:kev or evidence:proven or epss:>=0.088 or severity:critical',
		[QueueTier.Attend]: 'severity:high or severity:medium or evidence:corroborated',
		[QueueTier.Track]: ''
	};

	let columns = $derived(
		TIER_ORDER.map((tier) => ({
			tier,
			label: TIER_LABELS[tier],
			help: TIER_HELP[tier],
			count: risk.tiers[tier] ?? 0,
			cards: risk.queue.filter((f) => f.tier === tier).slice(0, PER_COLUMN),
			href: ROUTES.surface(
				VULN.tab,
				TIER_QUERY[tier] ? { [VULN.queryParam]: TIER_QUERY[tier] } : undefined
			)
		}))
	);

	const cardHref = (f: DashboardFinding) =>
		ROUTES.scanTab(f.scan_id, VULN.tab, { q: `template="${f.template_id}"` });
	const epss = (f: DashboardFinding) =>
		f.epss_score === null ? null : Math.round(f.epss_score * 100);
	const id = (f: DashboardFinding) => f.cve_ids[0] ?? f.template_id;
</script>

<Cell
	id="board"
	title="Findings"
	href={ROUTES.surface(VULN.tab)}
	hrefLabel="{risk.total.toLocaleString()} open"
	class={className}
	bodyClass="pt-2"
>
	<div class="grid gap-4 md:grid-cols-3">
		{#each columns as col (col.tier)}
			<div class="flex min-w-0 flex-col gap-2">
				<Hint text={col.help}>
					{#snippet child(props)}
						<a
							{...props}
							href={col.href}
							class="flex items-center justify-between rounded-md bg-muted/50 px-2.5 py-1.5 font-mono text-2xs tracking-[0.1em] text-muted-foreground uppercase hover:text-foreground"
						>
							<span>{col.label}</span>
							<span
								class="rounded bg-muted px-1.5 font-sans text-xs tracking-normal text-foreground tabular-nums normal-case"
							>
								{col.count.toLocaleString()}
							</span>
						</a>
					{/snippet}
				</Hint>
				{#each col.cards as f (f.id)}
					<HoverCard.Root openDelay={250}>
						<HoverCard.Trigger>
							{#snippet child({ props })}
								<a
									{...props}
									href={cardHref(f)}
									class="flex flex-col rounded-lg border bg-card transition-colors hover:border-ring/60 hover:bg-muted/30"
								>
									<span
										class="flex items-center justify-between gap-2 px-2.5 pt-2 font-mono text-2xs text-muted-foreground"
									>
										<span class="truncate">{id(f)}</span>
										{#if f.is_kev}
											<Badge variant="destructive" class="px-1.5 py-0 text-2xs">KEV</Badge>
										{:else if f.evidence === 'proven'}
											<Badge variant="success" class="px-1.5 py-0 text-2xs">Proven</Badge>
										{:else if f.is_new}
											<Badge variant="info" class="px-1.5 py-0 text-2xs">New</Badge>
										{:else if f.evidence && f.evidence !== 'observed'}
											<Badge variant="secondary" class="px-1.5 py-0 text-2xs">
												{evidenceLabel(f.evidence)}
											</Badge>
										{/if}
									</span>
									<span
										class="flex items-start gap-2 px-2.5 pt-1 pb-2 text-sm leading-5 font-medium"
									>
										<span class="flex h-5 shrink-0 items-center">
											<span
												class="size-2 rounded-full"
												style="background:{SEVERITY_FILL[f.severity] ?? 'var(--sev-info)'}"
											></span>
										</span>
										<span class="min-w-0">{f.name}</span>
									</span>
									<span
										class="flex flex-wrap items-center gap-x-3 gap-y-1 border-t px-2.5 py-1.5 text-2xs text-muted-foreground"
									>
										<span>{severityLabel(f.severity)}</span>
										{#if f.host}<span class="max-w-full min-w-0 truncate font-mono">{f.host}</span
											>{/if}
										{#if f.host_count > 1}
											<span class="tabular-nums">{f.host_count} web assets</span>
										{/if}
										{#if f.replays > 0}
											<span class="tabular-nums">{f.replays} replayed</span>
										{/if}
										{#if epss(f) !== null}
											<span class="ml-auto flex items-center gap-1.5 tabular-nums">
												{epss(f)}%
												<span class="h-1 w-10 overflow-hidden rounded-full bg-muted">
													<span class="block h-full bg-series" style="width:{epss(f)}%"></span>
												</span>
											</span>
										{:else}
											<span class="ml-auto">{relativeTime(f.discovered_at)}</span>
										{/if}
									</span>
								</a>
							{/snippet}
						</HoverCard.Trigger>
						<HoverCard.Content class="w-80 p-0" align="start" side="bottom">
							<div class="flex flex-col gap-1 border-b px-3 py-2.5">
								<span class="font-mono text-2xs text-muted-foreground">{f.template_id}</span>
								<span class="text-sm font-medium">{f.name}</span>
							</div>
							<dl class="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1.5 px-3 py-2.5 text-xs">
								<dt class="text-muted-foreground">Target</dt>
								<dd class="truncate font-mono">{f.target_value}</dd>
								<dt class="text-muted-foreground">Matched at</dt>
								<dd class="truncate font-mono">{f.matched_at}</dd>
								<dt class="text-muted-foreground">Severity</dt>
								<dd>
									{severityLabel(f.severity)}{#if f.cvss_score !== null}
										· CVSS {f.cvss_score}{/if}
								</dd>
								{#if f.epss_score !== null}
									<dt class="text-muted-foreground">EPSS</dt>
									<dd class="tabular-nums">{(f.epss_score * 100).toFixed(1)}%</dd>
								{/if}
								{#if f.cve_ids.length}
									<dt class="text-muted-foreground">CVE</dt>
									<dd class="font-mono">{f.cve_ids.join(', ')}</dd>
								{/if}
								<dt class="text-muted-foreground">Evidence</dt>
								<dd>
									{evidenceLabel(f.evidence) || 'Observed'}{#if f.replays > 0}
										· {f.replays} replayed{/if}
								</dd>
								<dt class="text-muted-foreground">Web assets</dt>
								<dd class="tabular-nums">{f.host_count}</dd>
								<dt class="text-muted-foreground">First seen</dt>
								<dd>{relativeTime(f.discovered_at)}</dd>
							</dl>
						</HoverCard.Content>
					</HoverCard.Root>
				{/each}
				{#if !col.cards.length}
					<span class="px-1 text-xs text-muted-foreground">None</span>
				{/if}
			</div>
		{/each}
	</div>
</Cell>
