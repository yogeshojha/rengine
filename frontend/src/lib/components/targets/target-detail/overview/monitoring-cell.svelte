<script lang="ts">
	import Info from '@lucide/svelte/icons/info';
	import Cell from '$lib/components/cell.svelte';
	import Hint from '$lib/components/hint.svelte';
	import { Switch } from '$lib/components/ui/switch';
	import { NEW_CHECKS_HELP, NEW_CHECKS_TITLE } from '$lib/config/new-checks';
	import { ROUTES } from '$lib/config/routes';
	import { formatShortDate, relativeTime } from '$lib/utilities/dates';
	import type { TargetSummaryRead } from '$lib/types/target-summary';

	interface Props {
		summary: TargetSummaryRead;
		enrichedAt: string | null;
		seedScans: boolean;
		onToggleSeeds: (on: boolean) => void;
		newChecks: boolean;
		onToggleNewChecks: (on: boolean) => void;
		onRefresh: () => void;
		class?: string;
	}

	let {
		summary,
		enrichedAt,
		seedScans,
		onToggleSeeds,
		newChecks,
		onToggleNewChecks,
		onRefresh,
		class: className = ''
	}: Props = $props();

	let monitoring = $derived(summary.monitoring);
</script>

<Cell
	skeleton="list"
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
					<a href={ROUTES.schedules} class="text-xs font-medium text-primary hover:text-primary/80"
						>Set a schedule</a
					>
				{/if}
			</dd>
		</div>
		<div class="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
			<dt class="pt-px text-xs text-muted-foreground">Runs</dt>
			<dd class="tabular-nums">
				{summary.scans_total.toLocaleString()}{#if summary.first_scan_at}<span
						class="text-muted-foreground"
						>{` · first ${formatShortDate(summary.first_scan_at)}`}</span
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
		<div class="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
			<dt class="pt-px text-xs text-muted-foreground">New checks</dt>
			<dd>
				<label class="flex items-center gap-2">
					<Switch
						checked={newChecks}
						onCheckedChange={onToggleNewChecks}
						aria-label={NEW_CHECKS_TITLE}
					/>
					<span class="text-sm"
						>{newChecks
							? summary.last_completed_at
								? 'Monitored'
								: 'Waits for a completed scan'
							: 'Not monitored'}</span
					>
					<Hint text={NEW_CHECKS_HELP}>
						{#snippet child(props)}
							<span {...props} class="flex h-5 items-center text-muted-foreground">
								<Info class="size-3.5" />
							</span>
						{/snippet}
					</Hint>
				</label>
			</dd>
		</div>
	</dl>
	{#snippet footer()}
		<span>{enrichedAt ? `Enriched ${relativeTime(enrichedAt)}` : 'Not enriched'}</span>
		<button
			type="button"
			class="font-medium text-primary hover:text-primary/80"
			onclick={onRefresh}
		>
			Refresh
		</button>
	{/snippet}
</Cell>
