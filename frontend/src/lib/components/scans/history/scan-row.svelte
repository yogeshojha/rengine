<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import GitCompare from '@lucide/svelte/icons/git-compare';
	import Play from '@lucide/svelte/icons/play';
	import Pause from '@lucide/svelte/icons/pause';
	import Ban from '@lucide/svelte/icons/ban';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import Hint from '$lib/components/hint.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { relativeTime, formatDateTime } from '$lib/utilities/dates';
	import { durationLabel, isLiveStatus, isOpenStatus } from '$lib/utilities/scan-status';
	import { INTENSITY_LABELS, type Intensity } from '$lib/types/scan-engine';
	import type { ScanRead, ScanTargetTrend } from '$lib/types/scan';
	import { COL } from './columns';
	import { historyPrefs } from './prefs.svelte';
	import TargetCell from './target-cell.svelte';
	import StatusCell from './status-cell.svelte';
	import SeverityChips from './severity-chips.svelte';
	import AssetsCell from './assets-cell.svelte';
	import ChangeCell from './change-cell.svelte';
	import RunBrief from './run-brief.svelte';

	interface Props {
		projectId: string;
		scan: ScanRead;
		showTarget: boolean;
		trend?: ScanTargetTrend;
		now: number;
		expanded: boolean;
		focused: boolean;
		selected: boolean;
		nested?: boolean;
		earlierOpen?: boolean;
		onEarlier?: () => void;
		onToggle: () => void;
		onSelect: () => void;
		onFocus: () => void;
		onOpen: () => void;
		onCompare: () => void;
		onRescan: () => void;
		onPause: () => void;
		onResume: () => void;
		onCancel: () => void;
		onDelete: () => void;
		onJump: (scanId: string) => void;
		onChanged: () => void;
	}

	let {
		projectId,
		scan,
		showTarget,
		trend,
		now,
		expanded,
		focused,
		selected,
		nested = false,
		earlierOpen = false,
		onEarlier,
		onToggle,
		onSelect,
		onFocus,
		onOpen,
		onCompare,
		onRescan,
		onPause,
		onResume,
		onCancel,
		onDelete,
		onJump,
		onChanged
	}: Props = $props();

	let live = $derived(isLiveStatus(scan.status));
	let open = $derived(isOpenStatus(scan.status));
	let highlight = $state<string | null>(null);
	let compact = $derived(historyPrefs.density === 'compact');
	let started = $derived(scan.started_at ?? scan.created_at);
</script>

<div
	id="scan-row-{scan.id}"
	class="group relative border-b border-border/60 transition-colors
		{expanded ? 'bg-muted/25' : ''} {selected ? 'bg-primary/5' : ''}"
>
	{#if focused}
		<span class="absolute inset-y-0 left-0 w-0.5 bg-primary" aria-hidden="true"></span>
	{/if}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="flex cursor-pointer items-center gap-3 px-4 {compact
			? 'py-1.5'
			: 'py-2.5'} hover:bg-muted/30 {nested ? 'pl-10' : ''}"
		role="row"
		tabindex="-1"
		aria-selected={selected}
		onclick={onOpen}
		onmouseenter={onFocus}
	>
		{#if nested}
			<span class="absolute top-0 bottom-0 left-6 w-px bg-border" aria-hidden="true"></span>
		{/if}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="{COL.select} flex items-center" onclick={(e) => e.stopPropagation()}>
			<Checkbox
				checked={selected}
				onCheckedChange={onSelect}
				aria-label="Select run of {scan.execution_config.target_value}"
				class="transition-opacity {selected ? '' : 'sm:opacity-0 sm:group-hover:opacity-100'}"
			/>
		</div>
		<div class={COL.target}>
			<TargetCell {scan} {showTarget} {trend} {now} {earlierOpen} {onEarlier} {onJump} />
		</div>
		<div class={COL.status}><StatusCell {scan} /></div>
		<div class={COL.findings}>
			<SeverityChips
				{projectId}
				scanId={scan.id}
				findings={scan.findings}
				live={open}
				{highlight}
			/>
		</div>
		{#if historyPrefs.shows('assets')}
			<div class={COL.assets}><AssetsCell {scan} /></div>
		{/if}
		{#if historyPrefs.shows('change')}
			<div class={COL.change}><ChangeCell {projectId} {scan} {onCompare} /></div>
		{/if}
		{#if historyPrefs.shows('engine')}
			<div class={COL.engine}>
				<div class="truncate text-sm">{scan.engine_name}</div>
				<div class="text-2xs text-muted-foreground">
					{INTENSITY_LABELS[scan.execution_config.intensity as Intensity] ??
						scan.execution_config.intensity}
				</div>
			</div>
		{/if}
		{#if historyPrefs.shows('duration')}
			<div
				class="{COL.duration} font-mono text-xs tabular-nums {live
					? 'text-info'
					: 'text-muted-foreground'}"
			>
				{durationLabel(scan, now)}
			</div>
		{/if}
		<div class="{COL.started} text-xs text-muted-foreground tabular-nums">
			<Hint text={formatDateTime(started)}>
				{#snippet child(props)}
					<span {...props}>{relativeTime(started)}</span>
				{/snippet}
			</Hint>
		</div>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="{COL.actions} items-center gap-0.5" onclick={(e) => e.stopPropagation()}>
			<Button
				variant="ghost"
				size="icon"
				class="size-7"
				aria-label={expanded ? 'Collapse run brief' : 'Expand run brief'}
				aria-expanded={expanded}
				onclick={onToggle}
			>
				<ChevronDown class="size-4 transition-transform {expanded ? 'rotate-180' : ''}" />
			</Button>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon" class="size-7" aria-label="Run actions">
							<Ellipsis class="size-4" />
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-52">
					<DropdownMenu.Item onSelect={onOpen}><ExternalLink /> Open results</DropdownMenu.Item>
					<DropdownMenu.Item onSelect={onCompare} disabled={!!scan.is_first_scan}>
						<GitCompare /> Compare with previous
					</DropdownMenu.Item>
					<DropdownMenu.Separator />
					{#if scan.status === 'paused'}
						<DropdownMenu.Item onSelect={onResume}><Play /> Resume</DropdownMenu.Item>
					{:else if scan.status === 'running'}
						<DropdownMenu.Item onSelect={onPause}><Pause /> Pause</DropdownMenu.Item>
					{/if}
					{#if open}
						<DropdownMenu.Item onSelect={onCancel}><Ban /> Cancel</DropdownMenu.Item>
					{:else}
						<DropdownMenu.Item onSelect={onRescan}><Play /> Run again</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onSelect={onDelete}
						><Trash2 /> Delete</DropdownMenu.Item
					>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>
	{#if expanded}
		<div class="px-4 pt-1 pb-4 {nested ? 'pl-10' : 'sm:pl-13'}">
			<RunBrief {projectId} {scan} {now} {onChanged} onHover={(s) => (highlight = s)} />
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<Button size="sm" class="h-8 gap-1.5" href={ROUTES.scan(scan.id)}>
					<ExternalLink class="size-3.5" /> Open results
				</Button>
				{#if !scan.is_first_scan}
					<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={onCompare}>
						<GitCompare class="size-3.5" /> Compare with previous
					</Button>
				{/if}
				{#if scan.status === 'running'}
					<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={onPause}>
						<Pause class="size-3.5" /> Pause
					</Button>
				{:else if scan.status === 'paused'}
					<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={onResume}>
						<Play class="size-3.5" /> Resume
					</Button>
				{/if}
				{#if open}
					<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={onCancel}>
						<Ban class="size-3.5" /> Cancel
					</Button>
				{:else}
					<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={onRescan}>
						<Play class="size-3.5" /> Run again
					</Button>
				{/if}
			</div>
		</div>
	{/if}
</div>
