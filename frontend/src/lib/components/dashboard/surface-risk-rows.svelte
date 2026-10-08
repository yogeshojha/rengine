<script lang="ts">
	import { scopeClause, useScopedRoutes } from './scope-links';
	import * as HoverCard from '$lib/components/ui/hover-card';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import {
		SEVERITY_FILL,
		SEVERITY_ORDER,
		Severity,
		severityLabel
	} from '$lib/config/vulnerabilities';
	import { SCAN_STATUS_LABEL, SCAN_STATUS_TEXT } from '$lib/utilities/scan-status';
	import { relativeTime } from '$lib/utilities/dates';
	import type { SurfaceRiskTarget } from '$lib/types/dashboard';

	const routes = useScopedRoutes();

	interface Props {
		rows: SurfaceRiskTarget[];
		severities?: string[];
		wide?: boolean;
		onScope?: (targetId: string) => void;
	}

	let { rows, severities = SEVERITY_ORDER, wide = false, onScope }: Props = $props();

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];
	const MIN = 2;
	const HOVER_SEVERITIES = SEVERITY_ORDER.filter(
		(s) => s !== Severity.INFO && s !== Severity.UNKNOWN
	);

	const shown = (r: SurfaceRiskTarget) =>
		severities.reduce((n, s) => n + (r.by_severity[s] ?? 0), 0);
	let maxLive = $derived(Math.max(1, ...rows.map((r) => r.live)));
	let maxShown = $derived(Math.max(1, ...rows.map(shown)));
	const pct = (n: number, max: number) => Math.max(MIN, (n / max) * 100);
	const liveQuery = (r: SurfaceRiskTarget) =>
		routes.results(WEB.tab, undefined, {
			[WEB.queryParam]: `${scopeClause([r.target_value])} and is:live`
		});
	const findingsQuery = (r: SurfaceRiskTarget) =>
		routes.results(VULNS.tab, undefined, {
			[VULNS.queryParam]: scopeClause([r.target_value])
		});
	let cols = $derived(
		wide
			? 'grid-cols-[minmax(0,1fr)_7rem_minmax(0,1fr)] sm:grid-cols-[minmax(0,1fr)_13.75rem_minmax(0,1fr)]'
			: 'grid-cols-[minmax(0,1fr)_7rem_minmax(0,1fr)] sm:grid-cols-[minmax(0,1fr)_10.5rem_minmax(0,1fr)]'
	);
</script>

<div class="flex flex-col">
	<div class="grid {cols} px-2 pb-1.5 text-2xs font-medium text-muted-foreground">
		<span class="text-right">Live web assets</span>
		<span class="text-center">Target</span>
		<span>Open findings</span>
	</div>
	{#each rows as r (r.target_id)}
		{@const total = shown(r)}
		{@const settled = !r.scan_status || r.scan_status === 'completed'}
		<HoverCard.Root openDelay={150} closeDelay={80}>
			<HoverCard.Trigger>
				{#snippet child({ props })}
					<svelte:element
						this={onScope ? 'button' : 'a'}
						{...props}
						type={onScope ? 'button' : undefined}
						href={onScope ? undefined : ROUTES.target(r.target_id)}
						onclick={onScope ? () => onScope(r.target_id) : undefined}
						aria-label={onScope ? `Scope to ${r.target_value}` : undefined}
						class="grid w-full {cols} min-h-9 items-center rounded-md text-left transition-colors hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					>
						<span class="flex items-center justify-end gap-2 pl-2">
							<span class="text-xs text-muted-foreground tabular-nums"
								>{r.live.toLocaleString()}</span
							>
							<span
								class="block h-4 rounded-sm"
								style="width:{r.live ? pct(r.live, maxLive) : 0}%;background:var(--series)"
							></span>
							{#if !r.live}<span class="block h-4 w-0.5 rounded-sm bg-border"></span>{/if}
						</span>
						<span class="flex min-w-0 flex-col items-center border-x px-2 text-center">
							<span class="max-w-full truncate text-xs font-semibold" title={r.target_value}
								>{r.target_value}</span
							>
							{#if r.actionable || !settled}
								<span
									class="flex flex-wrap items-center justify-center gap-x-1 text-2xs text-muted-foreground"
								>
									{#if r.actionable}
										<span class="font-semibold text-sev-critical-ink">
											{r.actionable.toLocaleString()} actionable
										</span>
									{/if}
									{#if !settled && r.scan_status}
										{#if r.actionable}<span>·</span>{/if}
										<span class={SCAN_STATUS_TEXT[r.scan_status]}
											>{SCAN_STATUS_LABEL[r.scan_status]}</span
										>
									{/if}
								</span>
							{/if}
						</span>
						<span class="flex items-center gap-2 pr-2">
							{#if total}
								<span class="flex h-4 gap-0.5" style="width:{pct(total, maxShown)}%">
									{#each severities as s (s)}
										{#if r.by_severity[s]}
											<span
												class="block h-full min-w-0.5 rounded-[2px] first:rounded-l-sm last:rounded-r-sm"
												style="flex:{r.by_severity[s]} 0 0;background:{SEVERITY_FILL[s]}"
											></span>
										{/if}
									{/each}
								</span>
							{:else}
								<span class="block h-4 w-0.5 rounded-sm bg-border"></span>
							{/if}
							<span class="text-xs text-muted-foreground tabular-nums"
								>{total.toLocaleString()}</span
							>
							{#if r.kev}
								<span
									class="shrink-0 rounded-sm bg-sev-critical-wash px-1.5 text-2xs font-semibold whitespace-nowrap text-sev-critical-ink"
								>
									KEV {r.kev}
								</span>
							{/if}
						</span>
					</svelte:element>
				{/snippet}
			</HoverCard.Trigger>
			<HoverCard.Content class="w-64 p-3" side="top" align="center">
				<div class="flex flex-col gap-2.5 text-xs">
					<div class="flex items-baseline justify-between gap-2">
						<a
							href={ROUTES.target(r.target_id)}
							title={r.target_value}
							class="truncate text-sm font-semibold hover:text-primary">{r.target_value}</a
						>
						<span class="shrink-0 text-2xs text-muted-foreground">
							{#if r.last_at}{relativeTime(
									r.last_at
								)}{/if}{#if !settled && r.scan_status}{` · ${SCAN_STATUS_LABEL[r.scan_status]}`}{/if}
						</span>
					</div>
					<div class="grid grid-cols-4 gap-1">
						{#each HOVER_SEVERITIES as s (s)}
							<div class="flex flex-col rounded-sm bg-muted px-1.5 py-1">
								<span class="text-sm font-semibold tabular-nums" style="color:{SEVERITY_FILL[s]}">
									{(r.by_severity[s] ?? 0).toLocaleString()}
								</span>
								<span class="text-2xs text-muted-foreground">{severityLabel(s)}</span>
							</div>
						{/each}
					</div>
					<a href={liveQuery(r)} class="flex justify-between gap-2 rounded-sm hover:text-primary">
						<span class="text-muted-foreground">Live web assets</span>
						<span class="font-medium tabular-nums"
							>{r.live.toLocaleString()} of {r.names.toLocaleString()}</span
						>
					</a>
					<a
						href={findingsQuery(r)}
						class="flex justify-between gap-2 rounded-sm hover:text-primary"
					>
						<span class="text-muted-foreground">Open findings</span>
						<span class="font-medium tabular-nums">{r.findings.toLocaleString()}</span>
					</a>
					<div class="flex justify-between gap-2">
						<span class="text-muted-foreground">Act now</span>
						<span class="font-medium tabular-nums">{r.act.toLocaleString()}</span>
					</div>
					{#if r.kev}
						<div class="flex justify-between gap-2">
							<span class="text-muted-foreground">Known exploited</span>
							<span class="font-medium text-sev-critical-ink tabular-nums">{r.kev}</span>
						</div>
					{/if}
				</div>
			</HoverCard.Content>
		</HoverCard.Root>
	{/each}
</div>
