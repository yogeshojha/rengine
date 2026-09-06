<script lang="ts">
	import { goto } from '$app/navigation';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Play from '@lucide/svelte/icons/play';
	import Ban from '@lucide/svelte/icons/ban';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import TrendingUp from '@lucide/svelte/icons/trending-up';
	import TrendingDown from '@lucide/svelte/icons/trending-down';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import Hint from '@/components/hint.svelte';
	import CopyButton from '@/components/copy-button.svelte';
	import ScanStatusBadge from '@/components/scan-status-badge.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { stopProp } from '$lib/utilities';
	import { SCHEDULE_TYPE_BADGE, type ScheduleType } from '$lib/types/scan-schedule';
	import { isLiveStatus, durationLabel, scanCountPills } from '$lib/utilities/scan-status';
	import { STAGE_STEP_CLASS, plannedStages, stageProgress } from '$lib/utilities/scan-progress';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { ROUTES } from '$lib/config/routes';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		scan: ScanRead;
		targetId?: string;
		now: number;
		selectable?: boolean;
		isSelected?: boolean;
		onSelect?: (id: string) => void;
		onRescan: (scan: ScanRead) => void;
		onCancel: (scan: ScanRead) => void;
		onDelete: (scan: ScanRead) => void;
	}

	let {
		scan,
		targetId,
		now,
		selectable = false,
		isSelected = false,
		onSelect,
		onRescan,
		onCancel,
		onDelete
	}: Props = $props();

	let live = $derived(isLiveStatus(scan.status));
	let primary = $derived(targetId ? scan.engine_name : scan.execution_config.target_value);
	let startedLabel = $derived(relativeTime(scan.started_at ?? scan.created_at));

	let newCount = $derived(scan.new_subdomains ?? 0);
	let goneCount = $derived(scan.gone_subdomains ?? 0);
	let prev = $derived(scan.prev_subdomains_found);
	let completed = $derived(scan.status === 'completed');
	let isFirst = $derived(scan.is_first_scan === true);
	let failedOrCancelled = $derived(scan.status === 'failed' || scan.status === 'cancelled');
	let authed = $derived(!!scan.auth_summary && scan.auth_summary !== 'None');
	let scheduleLabel = $derived(
		scan.schedule_type ? (SCHEDULE_TYPE_BADGE[scan.schedule_type as ScheduleType] ?? null) : null
	);
	let noResults = $derived(completed && scan.subdomains_found === 0);
	let dropAnomaly = $derived(
		completed && prev != null && prev >= 10 && scan.subdomains_found < prev * 0.3
	);
	let run = $derived(live ? liveScans.runFor(scan.id) : undefined);
	let progress = $derived(
		live ? stageProgress(scan, run, plannedStages(scan, engineCatalogStore.stages)) : null
	);

	function open() {
		goto(ROUTES.scan(scan.id));
	}
</script>

<div
	class="group flex items-center gap-3 px-4 py-2.5 transition-colors cursor-pointer {isSelected
		? 'bg-primary/5 hover:bg-primary/10'
		: 'hover:bg-muted/30'}"
	onclick={open}
	onkeydown={(e) => {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			open();
		}
	}}
	role="button"
	tabindex="0"
	aria-label="Open scan for {scan.execution_config.target_value}"
>
	{#if selectable}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="shrink-0" onclick={stopProp}>
			<Checkbox
				checked={isSelected}
				onCheckedChange={() => onSelect?.(scan.id)}
				aria-label="Select scan"
				class="transition-opacity {isSelected
					? 'opacity-100'
					: 'opacity-100 sm:opacity-0 sm:group-hover:opacity-100'}"
			/>
		</div>
	{/if}

	<div class="min-w-0 flex-1">
		<div class="flex min-w-0 items-center gap-2">
			<span class="font-mono text-sm font-medium truncate">{primary}</span>
			{#if !targetId}
				<CopyButton
					value={scan.execution_config.target_value}
					class="shrink-0 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
				/>
			{/if}
		</div>
		<div class="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
			{#if targetId}
				<span class="truncate">{scan.context_name ?? 'No context'}</span>
			{:else}
				<span class="flex min-w-0 items-center gap-1.5 lg:hidden">
					<span class="truncate">{scan.engine_name}</span>
					{#if scan.context_name}
						<span class="text-muted-foreground/40">·</span>
						<span class="truncate">{scan.context_name}</span>
					{/if}
				</span>
			{/if}

			{#if scheduleLabel}
				<Tooltip.Root>
					<Tooltip.Trigger
						class="inline-flex shrink-0 items-center gap-0.5 rounded border border-warning/30 px-1 font-medium text-warning"
					>
						<CalendarClock class="h-3 w-3 shrink-0" />
						{scheduleLabel}
					</Tooltip.Trigger>
					<Tooltip.Content>Scheduled scan · {scheduleLabel}</Tooltip.Content>
				</Tooltip.Root>
			{/if}

			{#if failedOrCancelled}
				{#if scan.error}
					<Tooltip.Root>
						<Tooltip.Trigger
							class="inline-flex max-w-[200px] shrink-0 items-center gap-0.5 rounded border border-destructive/30 px-1 font-medium text-destructive"
						>
							<TriangleAlert class="h-3 w-3 shrink-0" />
							<span class="truncate">{scan.error}</span>
						</Tooltip.Trigger>
						<Tooltip.Content>{scan.error}</Tooltip.Content>
					</Tooltip.Root>
				{/if}
			{:else if completed}
				{#if isFirst}
					<span
						class="inline-flex shrink-0 items-center gap-0.5 rounded border border-border px-1 font-medium"
					>
						<Sparkles class="h-3 w-3" />
						First scan
					</span>
				{:else}
					{#if newCount > 0}
						<span
							class="inline-flex shrink-0 items-center gap-0.5 rounded border border-warning/30 px-1 font-medium tabular-nums text-warning"
						>
							<TrendingUp class="h-3 w-3" />
							{newCount} new
						</span>
					{/if}
					{#if goneCount > 0 && !dropAnomaly}
						<span
							class="inline-flex shrink-0 items-center gap-0.5 rounded border border-border px-1 tabular-nums"
						>
							<TrendingDown class="h-3 w-3" />
							{goneCount} gone
						</span>
					{/if}
				{/if}
				{#if dropAnomaly}
					<Tooltip.Root>
						<Tooltip.Trigger
							class="inline-flex shrink-0 items-center gap-0.5 rounded border border-destructive/30 px-1 font-medium tabular-nums text-destructive"
						>
							<TrendingDown class="h-3 w-3" />
							{scan.subdomains_found} of {prev}
						</Tooltip.Trigger>
						<Tooltip.Content>
							Found far fewer than the previous scan ({prev}). The run may be incomplete.
						</Tooltip.Content>
					</Tooltip.Root>
				{:else if noResults && !isFirst}
					<span class="inline-flex shrink-0 items-center gap-0.5 rounded border border-border px-1">
						<CircleSlash class="h-3 w-3" />
						no results
					</span>
				{/if}
			{/if}

			{#if authed}
				<Tooltip.Root>
					<Tooltip.Trigger
						class="inline-flex shrink-0 items-center gap-0.5 rounded border border-border px-1"
					>
						<ShieldCheck class="h-3 w-3" />
						auth
					</Tooltip.Trigger>
					<Tooltip.Content>Authenticated · {scan.auth_summary}</Tooltip.Content>
				</Tooltip.Root>
			{/if}

			<span class="text-muted-foreground/40 sm:hidden">·</span>
			<span class="shrink-0 tabular-nums sm:hidden">{startedLabel}</span>
		</div>
	</div>

	{#if !targetId}
		<div class="hidden w-[150px] shrink-0 lg:block">
			<Hint text={scan.engine_name}>
				{#snippet child(props)}
					<div {...props} class="truncate text-sm">{scan.engine_name}</div>
				{/snippet}
			</Hint>
			<div class="mt-0.5 truncate text-xs text-muted-foreground">
				{scan.context_name ?? 'No context'}
			</div>
		</div>
	{/if}

	<div class="w-[120px] shrink-0">
		<ScanStatusBadge status={scan.status} />
	</div>

	<div class="hidden w-[220px] shrink-0 xl:block">
		{#if live && progress}
			<div class="flex items-center gap-2">
				{#if scan.status === 'running' && progress.steps.length > 0}
					<div
						class="flex w-16 shrink-0 gap-[2px]"
						role="img"
						aria-label="{progress.done} of {progress.total} stages complete"
					>
						{#each progress.steps as step (step.name)}
							<Hint text={step.title}>
								{#snippet child(props)}
									<span {...props} class="h-1 flex-1 rounded-full {STAGE_STEP_CLASS[step.state]}"
									></span>
								{/snippet}
							</Hint>
						{/each}
					</div>
				{/if}
				<span class="truncate text-xs text-muted-foreground">
					{scan.status === 'pending' ? 'Waiting to start' : progress.label}{#if run?.tool}
						<span class="font-mono"> · {run.tool}</span>{/if}
				</span>
			</div>
		{:else}
			<div class="flex flex-wrap gap-1">
				{#each scanCountPills(scan) as pill (pill.key)}
					{@const PillIcon = pill.icon}
					<Hint text={pill.label}>
						{#snippet child(props)}
							<Badge
								{...props}
								variant="outline"
								class="gap-1 font-normal tabular-nums {pill.emphasis
									? 'text-destructive border-destructive/40'
									: 'text-muted-foreground'}"
							>
								<PillIcon class="h-3 w-3" />
								{pill.value}
							</Badge>
						{/snippet}
					</Hint>
				{/each}
			</div>
		{/if}
	</div>

	<div
		class="hidden w-[80px] shrink-0 items-center justify-end text-right text-xs text-muted-foreground tabular-nums sm:flex"
	>
		{durationLabel(scan, now)}
	</div>

	<div
		class="hidden w-[120px] shrink-0 items-center justify-end text-right text-xs text-muted-foreground sm:flex"
	>
		{startedLabel}
	</div>

	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="flex w-8 shrink-0 items-center justify-end" onclick={stopProp}>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="h-8 w-8"
						aria-label="Actions for {scan.execution_config.target_value}"
					>
						<Ellipsis class="h-4 w-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-44">
				<DropdownMenu.Item onclick={open} class="gap-2">
					<ExternalLink class="h-4 w-4" /> Open
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => onRescan(scan)} class="gap-2">
					<Play class="h-4 w-4" /> Run again
				</DropdownMenu.Item>
				<DropdownMenu.Separator />
				{#if live}
					<DropdownMenu.Item onclick={() => onCancel(scan)} class="gap-2">
						<Ban class="h-4 w-4" /> Cancel
					</DropdownMenu.Item>
				{:else}
					<DropdownMenu.Item
						onclick={() => onDelete(scan)}
						class="gap-2 text-destructive focus:text-destructive"
					>
						<Trash2 class="h-4 w-4" /> Delete
					</DropdownMenu.Item>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
</div>
