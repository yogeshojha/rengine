<script lang="ts">
	import { useScopedRoutes } from './scope-links';
	import Cell from './cell.svelte';
	import SurfaceRiskRows from './surface-risk-rows.svelte';
	import SurfaceRiskDialog from './surface-risk-dialog.svelte';
	import { Button } from '$lib/components/ui/button';
	import { SEVERITY_FILL, SEVERITY_ORDER, severityLabel } from '$lib/config/vulnerabilities';
	import { ACT_QUERY, SURFACE_RISK_ROWS } from '$lib/config/dashboard';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { DashboardSurfaceRisk } from '$lib/types/dashboard';
	import type { TargetScope } from '$lib/utilities/surface-scope';

	const routes = useScopedRoutes();

	interface Props {
		data: DashboardSurfaceRisk | null;
		loading?: boolean;
		class?: string;
		onScope?: (scope: TargetScope) => void;
	}

	let { data, loading = false, class: className = '', onScope }: Props = $props();

	let open = $state(false);
	let rows = $derived((data?.rows ?? []).slice(0, SURFACE_RISK_ROWS));
	let present = $derived(
		SEVERITY_ORDER.filter((s) => (data?.rows ?? []).some((r) => r.by_severity[s]))
	);
	let more = $derived(Math.max(0, (data?.scanned ?? 0) - rows.length));

	const WEB = SURFACE[SurfaceDimension.WEB_ASSETS];
	const VULNS = SURFACE[SurfaceDimension.VULNERABILITIES];
	let liveHref = $derived(routes.results(WEB.tab, undefined, { [WEB.queryParam]: 'is:live' }));
	let findingsHref = $derived(routes.results(VULNS.tab));
	let actionableHref = $derived(
		routes.results(VULNS.tab, undefined, {
			[VULNS.queryParam]: 'severity:[critical,high,medium]'
		})
	);
	let actHref = $derived(routes.results(VULNS.tab, undefined, { [VULNS.queryParam]: ACT_QUERY }));
	const STAT = 'flex min-w-0 flex-col rounded-md bg-muted/60 px-2.5 py-1.5';
	const STAT_LINK = `${STAT} hover:bg-muted`;
</script>

<Cell
	id="surface-risk"
	title="Surface against risk"
	description="Live web assets against open findings, per target"
	loading={loading && !data}
	class={className}
>
	{#snippet tools()}
		{#if data}
			<Button variant="outline" size="sm" class="h-7 text-xs" onclick={() => (open = true)}>
				All targets
				<span class="text-muted-foreground tabular-nums">{data.targets_total.toLocaleString()}</span
				>
			</Button>
		{/if}
	{/snippet}
	{#if data}
		<div class="grid grid-cols-3 gap-2">
			<a href={liveHref} class={STAT_LINK}>
				<span class="text-lg leading-tight font-semibold tracking-tight tabular-nums">
					{data.live.toLocaleString()}
				</span>
				<span class="truncate text-2xs text-muted-foreground">live web assets</span>
			</a>
			<a href={findingsHref} class={STAT_LINK}>
				<span class="text-lg leading-tight font-semibold tracking-tight tabular-nums">
					{data.findings.toLocaleString()}
				</span>
				<span class="truncate text-2xs text-muted-foreground">open findings</span>
			</a>
			<div class={STAT}>
				<a
					href={actionableHref}
					class="text-lg leading-tight font-semibold tracking-tight tabular-nums hover:text-primary {data.actionable
						? 'text-[var(--sev-critical-ink)]'
						: ''}"
				>
					{data.actionable.toLocaleString()}
				</a>
				<span class="truncate text-2xs text-muted-foreground">
					actionable · <a href={actHref} class="hover:text-primary"
						>{data.act.toLocaleString()} act now</a
					>
				</span>
			</div>
		</div>
		{#if rows.length}
			<SurfaceRiskRows {rows} onScope={onScope && ((id) => onScope({ targetIds: [id] }))} />
		{:else}
			<p class="py-6 text-center text-sm text-muted-foreground">Not scanned</p>
		{/if}
	{:else}
		<p class="py-6 text-center text-sm text-muted-foreground">Surface against risk not loaded.</p>
	{/if}
	{#snippet footer()}
		<div class="flex flex-wrap items-center gap-x-3 gap-y-1">
			<span class="flex items-center gap-1.5">
				<span class="size-2.5 rounded-[2px]" style="background:var(--series)"></span>
				Live web assets
			</span>
			{#each present as s (s)}
				<span class="flex items-center gap-1.5">
					<span class="size-2.5 rounded-[2px]" style="background:{SEVERITY_FILL[s]}"></span>
					{severityLabel(s)}
				</span>
			{/each}
		</div>
		{#if more}
			<span>{more.toLocaleString()} more scanned targets</span>
		{/if}
	{/snippet}
</Cell>

<SurfaceRiskDialog bind:open {onScope} />
