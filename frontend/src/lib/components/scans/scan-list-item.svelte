<script lang="ts">
	import { goto } from '$app/navigation';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import {
		Ellipsis,
		ExternalLink,
		Play,
		Ban,
		Trash2,
		TrendingUp,
		TrendingDown,
		CircleSlash,
		Sparkles,
		ShieldCheck,
		TriangleAlert,
		CalendarClock
	} from 'lucide-svelte';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import CopyButton from '@/components/copy-button.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { stopProp } from '$lib/utilities';
	import { SCHEDULE_TYPE_BADGE, type ScheduleType } from '$lib/types/scan-schedule';
	import {
		SCAN_STATUS_LABEL,
		scanStatusVariant,
		scanStatusIcon,
		isLiveStatus,
		durationLabel,
		scanCountPills
	} from '$lib/utilities/scan-status';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		scan: ScanRead;
		targetId?: string;
		now: number;
		onRescan: (scan: ScanRead) => void;
		onCancel: (scan: ScanRead) => void;
		onDelete: (scan: ScanRead) => void;
	}

	let { scan, targetId, now, onRescan, onCancel, onDelete }: Props = $props();

	let StatusIcon = $derived(scanStatusIcon(scan.status));
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

	function open() {
		goto(`/scans/${scan.id}`);
	}
</script>

<div
	class="group flex items-center gap-3 px-4 py-2.5 transition-colors cursor-pointer hover:bg-muted/30"
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
				<span class="truncate">{scan.engine_name}</span>
				{#if scan.context_name}
					<span class="text-muted-foreground/40">·</span>
					<span class="truncate">{scan.context_name}</span>
				{/if}
			{/if}

			{#if scheduleLabel}
				<Tooltip.Root>
					<Tooltip.Trigger
						class="inline-flex shrink-0 items-center gap-0.5 rounded border border-amber-500/30 px-1 font-medium text-amber-600 dark:text-amber-500"
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
							class="inline-flex shrink-0 items-center gap-0.5 rounded border border-amber-500/30 px-1 font-medium tabular-nums text-amber-600 dark:text-amber-500"
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
							Found far fewer than the previous scan ({prev}) — possible incomplete run.
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

	<div class="w-[120px] shrink-0">
		<Badge variant={scanStatusVariant(scan.status)} class="gap-1 font-normal">
			<StatusIcon class="h-3 w-3 {scan.status === 'running' ? 'animate-spin' : ''}" />
			{SCAN_STATUS_LABEL[scan.status]}
		</Badge>
	</div>

	<div class="hidden w-[220px] shrink-0 xl:block">
		{#if live}
			<span class="text-xs text-muted-foreground">{scan.subdomains_found} subs · scanning…</span>
		{:else}
			<div class="flex flex-wrap gap-1">
				{#each scanCountPills(scan) as pill (pill.key)}
					{@const PillIcon = pill.icon}
					<Badge
						variant="outline"
						title={pill.label}
						class="gap-1 font-normal tabular-nums {pill.emphasis
							? 'text-destructive border-destructive/40'
							: 'text-muted-foreground'}"
					>
						<PillIcon class="h-3 w-3" />
						{pill.value}
					</Badge>
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
					<Play class="h-4 w-4" /> Re-scan
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
