<script lang="ts">
	import { errorMessage } from '$lib/utilities/errors';
	import { goto } from '$app/navigation';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
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
	import { clipped } from '$lib/utilities/clipped';
	import { SCHEDULE_TYPE_BADGE, type ScheduleType } from '$lib/types/scan-schedule';
	import { isLiveStatus, durationLabel, scanCountPills } from '$lib/utilities/scan-status';
	import { STAGE_STEP_CLASS, plannedStages, stageProgress } from '$lib/utilities/scan-progress';
	import Pause from '@lucide/svelte/icons/pause';
	import ScanListItem from './scan-list-item.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { engineCatalogStore } from '$lib/stores/engine-catalog.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, type SurfaceDimension } from '$lib/config/surface';
	import type { ScanRead } from '$lib/types/scan';

	const RESCAN_PAGE = 10;
	const MOVED_SHOWN = 3;

	interface Props {
		scan: ScanRead;
		targetId?: string;
		nested?: boolean;
		now: number;
		selectable?: boolean;
		isSelected?: boolean;
		onSelect?: (id: string) => void;
		onRescan: (scan: ScanRead) => void;
		onCancel: (scan: ScanRead) => void;
		onPause: (scan: ScanRead) => void;
		onResume: (scan: ScanRead) => void;
		onDelete: (scan: ScanRead) => void;
	}

	let {
		scan,
		targetId,
		nested = false,
		now,
		selectable = false,
		isSelected = false,
		onSelect,
		onRescan,
		onCancel,
		onPause,
		onResume,
		onDelete
	}: Props = $props();

	let errorClipped = $state(false);
	let engineClipped = $state(false);

	let rescansOpen = $state(false);
	let rescansLoading = $state(false);
	let rescansError = $state<string | null>(null);
	let rescanRuns = $state<ScanRead[]>([]);
	let rescanTotal = $state(0);

	let rescans = $derived(nested ? null : scan.rescans);
	let moved = $derived(scan.recheck?.fields ?? []);

	async function loadRescans(size: number) {
		rescansLoading = true;
		rescansError = null;
		try {
			const page = await scansStore.loadRescans(scan.id, size);
			rescanRuns = page.items;
			rescanTotal = page.total;
		} catch (e) {
			rescanRuns = [];
			rescansError = errorMessage(e, 'Rechecks not loaded.');
		} finally {
			rescansLoading = false;
		}
	}

	function toggleRescans() {
		rescansOpen = !rescansOpen;
		if (rescansOpen && rescanRuns.length === 0 && !rescansLoading) void loadRescans(RESCAN_PAGE);
	}

	let live = $derived(isLiveStatus(scan.status));
	let paused = $derived(scan.status === 'paused');
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

<div>
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
				{#if nested}
					{#if !scan.recheck}
						<span class="shrink-0 tabular-nums">
							{scan.seed_count}
							{scan.seed_count === 1 ? 'asset' : 'assets'}
						</span>
					{/if}
				{:else if targetId}
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

				{#if rescans && rescans.total > 0}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<span class="shrink-0" onclick={stopProp}>
						<button
							type="button"
							class="inline-flex items-center gap-0.5 rounded border border-border px-1 font-medium hover:bg-muted"
							aria-expanded={rescansOpen}
							onclick={toggleRescans}
						>
							<ChevronRight class="h-3 w-3 transition-transform {rescansOpen ? 'rotate-90' : ''}" />
							{rescans.total}
							{rescans.total === 1 ? 'rescan' : 'rescans'}
						</button>
					</span>
					{#if rescans.running > 0}
						<span
							class="inline-flex shrink-0 items-center gap-0.5 rounded border border-info/30 px-1 font-medium text-info"
						>
							<span class="h-1.5 w-1.5 rounded-full bg-info"></span>
							{rescans.running} running
						</span>
					{:else if rescans.failed > 0}
						<span
							class="inline-flex shrink-0 items-center gap-0.5 rounded border border-destructive/30 px-1 font-medium text-destructive"
						>
							{rescans.failed} failed
						</span>
					{/if}
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
						<Hint text={errorClipped ? scan.error : null}>
							{#snippet child(props)}
								<span
									{...props}
									class="inline-flex max-w-[200px] shrink-0 items-center gap-0.5 rounded border border-destructive/30 px-1 font-medium text-destructive"
								>
									<TriangleAlert class="h-3 w-3 shrink-0" />
									<span
										class="truncate"
										use:clipped={{ value: scan.error, onChange: (v) => (errorClipped = v) }}
									>
										{scan.error}
									</span>
								</span>
							{/snippet}
						</Hint>
					{/if}
				{:else if completed && !nested}
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
							<Tooltip.Content>Previous scan found {prev}.</Tooltip.Content>
						</Tooltip.Root>
					{:else if noResults && !isFirst}
						<span
							class="inline-flex shrink-0 items-center gap-0.5 rounded border border-border px-1"
						>
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
				<Hint text={engineClipped ? scan.engine_name : null}>
					{#snippet child(props)}
						<div
							{...props}
							class="truncate text-sm"
							use:clipped={{ value: scan.engine_name, onChange: (v) => (engineClipped = v) }}
						>
							{scan.engine_name}
						</div>
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
						{scan.status === 'pending' ? 'Queued' : progress.label}{#if run?.tool}
							<span class="font-mono"> · {run.tool}</span>{/if}
					</span>
				</div>
			{:else if nested}
				{#if moved.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each moved.slice(0, MOVED_SHOWN) as field (field.field)}
							{@const FieldIcon = SURFACE[field.dimension as SurfaceDimension]?.icon}
							<Hint text={field.label}>
								{#snippet child(props)}
									<Badge
										{...props}
										variant="outline"
										class="gap-0.5 font-normal tabular-nums text-muted-foreground"
									>
										{#if FieldIcon}<FieldIcon class="h-3 w-3" />{/if}
										{#if field.up > 0}
											<TrendingUp class="h-3 w-3" />{field.up}
										{/if}
										{#if field.down > 0}
											<TrendingDown class="h-3 w-3" />{field.down}
										{/if}
									</Badge>
								{/snippet}
							</Hint>
						{/each}
						{#if moved.length > MOVED_SHOWN}
							<Hint
								text={moved
									.slice(MOVED_SHOWN)
									.map((f) => f.label)
									.join(', ')}
							>
								{#snippet child(props)}
									<Badge
										{...props}
										variant="outline"
										class="font-normal tabular-nums text-muted-foreground"
									>
										+{moved.length - MOVED_SHOWN}
									</Badge>
								{/snippet}
							</Hint>
						{/if}
					</div>
				{:else if scan.recheck}
					<Badge variant="outline" class="font-normal text-muted-foreground">No change</Badge>
				{/if}
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
						<DropdownMenu.Item onclick={() => onPause(scan)} class="gap-2">
							<Pause class="h-4 w-4" /> Pause
						</DropdownMenu.Item>
						<DropdownMenu.Item onclick={() => onCancel(scan)} class="gap-2">
							<Ban class="h-4 w-4" /> Cancel
						</DropdownMenu.Item>
					{:else if paused}
						<DropdownMenu.Item onclick={() => onResume(scan)} class="gap-2">
							<Play class="h-4 w-4" /> Resume
						</DropdownMenu.Item>
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

	{#if rescansOpen}
		<div class="border-t border-border/50 bg-muted/20 pl-6">
			{#if rescansLoading && rescanRuns.length === 0}
				<div class="space-y-2 px-4 py-3">
					{#each Array(2) as _, i (i)}
						<Skeleton class="h-8 w-full" />
					{/each}
				</div>
			{:else if rescansError}
				<div class="px-4 py-4 text-xs text-muted-foreground">
					Rechecks not loaded. {rescansError}
				</div>
			{:else if rescanRuns.length === 0}
				<div class="px-4 py-4 text-xs text-muted-foreground">No rescans.</div>
			{:else}
				<div class="divide-y divide-border/50">
					{#each rescanRuns as run (run.id)}
						<ScanListItem
							scan={run}
							targetId={run.target_id}
							nested
							{now}
							{onRescan}
							{onCancel}
							{onPause}
							{onResume}
							{onDelete}
						/>
					{/each}
				</div>
				{#if rescanRuns.length < rescanTotal}
					<div class="flex items-center gap-3 px-4 py-2 text-xs text-muted-foreground">
						<span class="tabular-nums">Showing {rescanRuns.length} of {rescanTotal}</span>
						<Button
							variant="ghost"
							size="sm"
							class="h-7 px-2 text-xs"
							disabled={rescansLoading}
							onclick={() => loadRescans(rescanRuns.length + RESCAN_PAGE)}
						>
							Show {Math.min(RESCAN_PAGE, rescanTotal - rescanRuns.length)} more
						</Button>
					</div>
				{/if}
			{/if}
		</div>
	{/if}
</div>
