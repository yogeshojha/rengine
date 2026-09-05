<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Flame from '@lucide/svelte/icons/flame';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import PanelHead from '$lib/components/panel-head.svelte';
	import SeverityBar from '$lib/components/scans/results/vulnerabilities/severity-bar.svelte';
	import SeverityMark from '$lib/components/scans/results/vulnerabilities/severity-mark.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import { formatShortDate } from '$lib/utilities/dates';
	import type { TargetRisk } from '$lib/types/target-summary';

	interface Props {
		risk: TargetRisk;
	}

	let { risk }: Props = $props();

	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];

	let rows = $derived(risk.by_severity.filter((s) => s.count > 0));
	let observed = $derived(risk.observed_at ? formatShortDate(risk.observed_at) : '');
	let worst = $derived(rows[0]);
	let headline = $derived.by(() => {
		if (risk.total === 0) return 'No findings';
		if (risk.actionable === 0) return `${risk.total.toLocaleString()} informational findings`;
		return `${risk.actionable.toLocaleString()} findings need attention`;
	});

	const href = (query?: string) =>
		risk.scan_id
			? ROUTES.scanTab(risk.scan_id, VULNS.tab, query ? { [VULNS.queryParam]: query } : undefined)
			: '#';
</script>

<Card.Root class="gap-0 overflow-hidden py-0">
	<PanelHead title="Risk" description="From the most recent scan that ran vulnerability checks">
		{#if observed}
			<span class="tabular-nums">{observed}</span>
		{/if}
	</PanelHead>

	<div class="flex flex-col gap-4 px-5 py-4">
		<div class="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
			<span class="text-lg font-semibold tracking-tight">{headline}</span>
			{#if risk.kev > 0}
				<a
					href={href('is:kev')}
					class="inline-flex h-6 items-center gap-1 rounded-md border border-destructive/30 px-2 text-xs font-medium text-destructive transition-colors hover:bg-destructive/5"
				>
					<Flame class="size-3.5" />
					<span class="tabular-nums">{risk.kev.toLocaleString()}</span>
					known exploited
				</a>
			{/if}
		</div>

		{#if rows.length > 0}
			<SeverityBar counts={risk.by_severity} />
			<ul class="-mx-2 flex flex-col gap-0.5">
				{#each rows as row (row.severity)}
					<li>
						<a
							href={href(`severity:${row.severity}`)}
							class="flex items-center gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-muted/50"
						>
							<span class="flex h-5 items-center">
								<SeverityMark severity={row.severity} showLabel={false} />
							</span>
							<span class="min-w-0 flex-1 truncate text-sm leading-5">{row.label}</span>
							<span class="text-sm font-medium tabular-nums">{row.count.toLocaleString()}</span>
						</a>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="text-sm text-muted-foreground">
				The checks ran and reported nothing. Open the scan to see what was covered.
			</p>
		{/if}

		{#if risk.suppressed > 0}
			<p class="text-xs text-muted-foreground">
				{risk.suppressed.toLocaleString()} suppressed by review, not counted here.
			</p>
		{/if}

		{#if risk.scan_id}
			<Button variant="link" size="sm" href={href()} class="h-auto gap-1 self-start px-0 text-xs">
				Open {worst ? 'findings' : 'coverage'}
				<ChevronRight class="size-3.5" />
			</Button>
		{/if}
	</div>
</Card.Root>
