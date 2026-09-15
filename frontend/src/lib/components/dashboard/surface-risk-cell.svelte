<script lang="ts">
	import Cell from './cell.svelte';
	import SurfaceRiskRows from './surface-risk-rows.svelte';
	import SurfaceRiskDialog from './surface-risk-dialog.svelte';
	import { Button } from '$lib/components/ui/button';
	import { SEVERITY_FILL, SEVERITY_ORDER, severityLabel } from '$lib/config/vulnerabilities';
	import { SURFACE_RISK_ROWS } from '$lib/config/dashboard';
	import type { DashboardSurfaceRisk } from '$lib/types/dashboard';

	interface Props {
		data: DashboardSurfaceRisk | null;
		loading?: boolean;
		class?: string;
	}

	let { data, loading = false, class: className = '' }: Props = $props();

	let open = $state(false);
	let rows = $derived((data?.rows ?? []).slice(0, SURFACE_RISK_ROWS));
	let present = $derived(
		SEVERITY_ORDER.filter((s) => (data?.rows ?? []).some((r) => r.by_severity[s]))
	);
	let more = $derived(Math.max(0, (data?.scanned ?? 0) - rows.length));
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
			<div class="flex min-w-0 flex-col rounded-md bg-muted/60 px-2.5 py-1.5">
				<span class="text-lg leading-tight font-semibold tracking-tight tabular-nums">
					{data.live.toLocaleString()}
				</span>
				<span class="truncate text-2xs text-muted-foreground">live web assets</span>
			</div>
			<div class="flex min-w-0 flex-col rounded-md bg-muted/60 px-2.5 py-1.5">
				<span class="text-lg leading-tight font-semibold tracking-tight tabular-nums">
					{data.findings.toLocaleString()}
				</span>
				<span class="truncate text-2xs text-muted-foreground">open findings</span>
			</div>
			<div class="flex min-w-0 flex-col rounded-md bg-muted/60 px-2.5 py-1.5">
				<span
					class="text-lg leading-tight font-semibold tracking-tight tabular-nums {data.actionable
						? 'text-[var(--sev-critical-ink)]'
						: ''}"
				>
					{data.actionable.toLocaleString()}
				</span>
				<span class="truncate text-2xs text-muted-foreground">
					actionable · {data.act.toLocaleString()} act now
				</span>
			</div>
		</div>
		{#if rows.length}
			<SurfaceRiskRows {rows} />
		{:else}
			<p class="py-6 text-center text-sm text-muted-foreground">Not scanned</p>
		{/if}
	{:else}
		<p class="py-6 text-center text-sm text-muted-foreground">Surface against risk did not load.</p>
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

<SurfaceRiskDialog bind:open />
