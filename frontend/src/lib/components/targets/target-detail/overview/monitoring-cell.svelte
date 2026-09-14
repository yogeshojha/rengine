<script lang="ts">
	import Cell from '$lib/components/cell.svelte';
	import { Switch } from '$lib/components/ui/switch';
	import { ROUTES } from '$lib/config/routes';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import type { TargetSummaryRead } from '$lib/types/target-summary';

	interface Props {
		summary: TargetSummaryRead;
		enrichedAt: string | null;
		seedScans: boolean;
		onToggleSeeds: (on: boolean) => void;
		onRefresh: () => void;
		class?: string;
	}

	let {
		summary,
		enrichedAt,
		seedScans,
		onToggleSeeds,
		onRefresh,
		class: className = ''
	}: Props = $props();

	let monitoring = $derived(summary.monitoring);
</script>

<Cell
	id="monitoring"
	title="Monitoring"
	href={ROUTES.schedules}
	hrefLabel="Schedules"
	class={className}
>
	<dl class="flex flex-col gap-1.5 text-sm">
		<div class="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
			<dt class="pt-px text-xs text-muted-foreground">Schedule</dt>
			<dd class="flex min-w-0 flex-col">
				{#if monitoring}
					<span>{monitoring.cadence}</span>
					{#if monitoring.next_run_at}
						<span class="text-xs text-muted-foreground"
							>next {formatShortDate(monitoring.next_run_at)}</span
						>
					{/if}
				{:else}
					<span>Not scheduled</span>
					<a href={ROUTES.schedules} class="text-xs font-medium text-primary">Set a schedule</a>
				{/if}
			</dd>
		</div>
		<div class="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
			<dt class="pt-px text-xs text-muted-foreground">Runs</dt>
			<dd class="tabular-nums">
				{summary.scans_total.toLocaleString()}{#if summary.first_scan_at}<span
						class="text-muted-foreground"
					>
						· first {formatShortDate(summary.first_scan_at)}</span
					>{/if}
			</dd>
		</div>
		<div class="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
			<dt class="pt-px text-xs text-muted-foreground">Seeds</dt>
			<dd>
				<label class="flex items-center gap-2">
					<Switch
						checked={seedScans}
						onCheckedChange={onToggleSeeds}
						aria-label="Seed scans of this target"
					/>
					<span class="text-sm"
						>{seedScans ? 'Scans start from stored assets' : 'Stored, not used'}</span
					>
				</label>
			</dd>
		</div>
	</dl>
	{#snippet footer()}
		<span>{enrichedAt ? `Enriched ${relativeTime(enrichedAt)}` : 'Not enriched'}</span>
		<button type="button" class="font-medium text-primary hover:underline" onclick={onRefresh}>
			Refresh
		</button>
	{/snippet}
</Cell>
