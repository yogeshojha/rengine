<script lang="ts">
	import { goto } from '$app/navigation';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import GitCompare from '@lucide/svelte/icons/git-compare';
	import History from '@lucide/svelte/icons/history';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Play from '@lucide/svelte/icons/play';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { Button } from '$lib/components/ui/button';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Input } from '$lib/components/ui/input';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CopyButton from '$lib/components/copy-button.svelte';
	import Hint from '$lib/components/hint.svelte';
	import WhoisInline from '$lib/components/targets/whois-inline.svelte';
	import BgpInline from '$lib/components/targets/bgp-inline.svelte';
	import DnsInline from '$lib/components/targets/dns-inline.svelte';
	import TargetInfraBadge from '$lib/components/targets/target-infra-badge.svelte';
	import TargetOrgPopover from '$lib/components/targets/target-org-popover.svelte';
	import TargetTagPopover from '$lib/components/targets/target-tag-popover.svelte';
	import DiscoveryBadge from '$lib/components/viewdns-discoveries/discovery-badge.svelte';
	import StatusCell from '$lib/components/scans/history/status-cell.svelte';
	import SeverityChips from '$lib/components/scans/history/severity-chips.svelte';
	import AssetsCell from '$lib/components/scans/history/assets-cell.svelte';
	import ChangeCell from '$lib/components/scans/history/change-cell.svelte';
	import TrendSpark from '$lib/components/scans/history/trend-spark.svelte';
	import RunBrief from '$lib/components/scans/history/run-brief.svelte';
	import { ROUTES } from '$lib/config/routes';
	import {
		bgpApplies,
		dnsApplies,
		formatTargetType,
		type EnrichmentKind,
		type Target
	} from '$lib/types/target';
	import type { ScanRead, ScanTargetTrend } from '$lib/types/scan';
	import { formatDateTime, relativeTime } from '$lib/utilities/dates';
	import { isOpenStatus } from '$lib/utilities/scan-status';
	import { stopProp } from '$lib/utilities';
	import { TCOL, TNARROW } from './columns';
	import { targetPrefs } from './prefs.svelte';

	interface Props {
		projectId: string;
		target: Target;
		run: ScanRead | undefined;
		trend: ScanTargetTrend | undefined;
		loaded: boolean;
		now: number;
		index: number;
		expanded: boolean;
		focused: boolean;
		selected: boolean;
		scanning: boolean;
		onToggle: () => void;
		onSelect: () => void;
		onFocus: () => void;
		onScan: () => void;
		onSchedule: () => void;
		onHistory: () => void;
		onCompare: (run: ScanRead) => void;
		onDelete: () => void;
		onRename: (name: string) => void;
		onReEnrich: (kind: EnrichmentKind) => void;
		onWhois: () => void;
		onDiscoveries: () => void;
		onBgp: () => void;
		onDns: () => void;
		onInfra: () => void;
		onChanged: () => void;
	}

	let {
		projectId,
		target,
		run,
		trend,
		loaded,
		now,
		index,
		expanded,
		focused,
		selected,
		scanning,
		onToggle,
		onSelect,
		onFocus,
		onScan,
		onSchedule,
		onHistory,
		onCompare,
		onDelete,
		onRename,
		onReEnrich,
		onWhois,
		onDiscoveries,
		onBgp,
		onDns,
		onInfra,
		onChanged
	}: Props = $props();

	let compact = $derived(targetPrefs.density === 'compact');
	let open = $derived(run ? isOpenStatus(run.status) : false);
	let findingsScan = $derived(run?.findings?.scan_id ?? run?.id ?? '');
	let findingsLive = $derived(open && findingsScan === run?.id);
	let started = $derived(run ? (run.started_at ?? run.created_at) : null);
	let canDns = $derived(dnsApplies(target.target_type));
	let canBgp = $derived(bgpApplies(target.target_type));
	let highlight = $state<string | null>(null);

	let editing = $state(false);
	let editValue = $state('');
	let renameInput = $state<HTMLInputElement | null>(null);
	$effect(() => {
		if (editing) renameInput?.focus();
	});

	function startRename() {
		editValue = target.display_name || target.target_value;
		editing = true;
	}

	function commitRename() {
		if (!editing) return;
		editing = false;
		const next = editValue.trim();
		if (next && next !== target.display_name) onRename(next);
	}
</script>

<div
	id="target-row-{target.id}"
	class="group relative border-b border-border/60 transition-colors
		{selected ? 'bg-primary/5' : focused || expanded ? 'bg-muted/30' : ''}"
>
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div
		class="flex cursor-pointer items-center gap-3 px-4 hover:bg-muted/30 {compact
			? 'py-1.5'
			: 'py-2.5'}"
		role="row"
		tabindex="-1"
		aria-selected={selected}
		data-target-row-index={index}
		onclick={onToggle}
		onmouseenter={onFocus}
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="{TCOL.select} h-6" onclick={stopProp}>
			<Checkbox
				checked={selected}
				onCheckedChange={onSelect}
				aria-label="Select {target.target_value}"
				class="transition-opacity {selected
					? ''
					: 'sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100'}"
			/>
		</div>

		<div class="{TCOL.target} flex items-start gap-3">
			<div class="min-w-0 flex-1">
				<div class="flex min-w-0 items-center gap-1.5">
					<a
						href={ROUTES.target(target.id)}
						class="truncate font-mono text-sm font-medium hover:text-primary"
						onclick={stopProp}>{target.target_value}</a
					>
					<CopyButton
						value={target.target_value}
						class="shrink-0 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
					/>
				</div>
				{#if editing}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div onclick={stopProp} class="mt-0.5 max-w-[280px]">
						<Input
							bind:ref={renameInput}
							value={editValue}
							oninput={(e) => (editValue = e.currentTarget.value)}
							onblur={commitRename}
							onkeydown={(e) => {
								if (e.key === 'Enter') commitRename();
								else if (e.key === 'Escape') editing = false;
							}}
							class="h-6 text-xs"
							placeholder="Display name"
						/>
					</div>
				{:else}
					<div
						class="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5 text-2xs text-muted-foreground"
					>
						<span class="rounded border border-border/70 px-1 font-mono uppercase">
							{formatTargetType(target.target_type)}
						</span>
						{#if target.display_name && target.display_name !== target.target_value}
							<span class="truncate">{target.display_name}</span>
						{/if}
						{#if targetPrefs.folded('run')}
							{#if run}
								<span>Run {relativeTime(started)}</span>
							{:else if loaded}
								<span>Not scanned</span>
							{:else}
								<Skeleton class="h-3 w-16" />
							{/if}
						{/if}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<span class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5" onclick={stopProp}>
							<WhoisInline
								status={target.whois_status}
								whois={target.whois}
								error={target.whois_error}
								targetId={target.id}
								onClick={onWhois}
							/>
							<DnsInline
								status={target.dns_status}
								dns={target.dns}
								targetType={target.target_type}
								targetValue={target.target_value}
								targetId={target.id}
								onClick={onDns}
							/>
							<BgpInline
								status={target.bgp_status}
								bgp={target.bgp}
								targetType={target.target_type}
								targetValue={target.target_value}
								onClick={onBgp}
							/>
							<TargetInfraBadge
								targetId={target.id}
								whoisRecordId={target.whois_record_id}
								onClick={onInfra}
							/>
							<DiscoveryBadge
								targetValue={target.target_value}
								targetType={target.target_type}
								whois={target.whois}
								onClick={onDiscoveries}
							/>
						</span>
					</div>
				{/if}
				{#if run?.findings?.covered && targetPrefs.folded('findings')}
					<div class="mt-1">
						<SeverityChips
							{projectId}
							scanId={findingsScan}
							findings={run.findings}
							live={findingsLive}
						/>
					</div>
				{/if}
			</div>
			{#if trend && run && trend.points.length > 1}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div class={TNARROW.spark} onclick={stopProp}>
					<TrendSpark
						points={trend.points}
						current={run.id}
						onJump={(id) => goto(ROUTES.scan(id))}
					/>
				</div>
			{/if}
		</div>

		{#if targetPrefs.fits('run')}
			<div class="{TCOL.run} flex-col gap-1">
				{#if run}
					<StatusCell scan={run} />
					<Hint text={started ? formatDateTime(started) : null}>
						{#snippet child(props)}
							<span {...props} class="w-fit text-2xs text-muted-foreground tabular-nums"
								>{relativeTime(started)}</span
							>
						{/snippet}
					</Hint>
				{:else if loaded}
					<span class="text-xs leading-6 text-muted-foreground">Not scanned</span>
				{:else}
					<Skeleton class="h-6 w-24 rounded-md" />
					<Skeleton class="h-3 w-12" />
				{/if}
			</div>
		{/if}

		{#if targetPrefs.fits('findings')}
			<div class="{TCOL.findings} h-6 items-center">
				{#if run}
					<SeverityChips
						{projectId}
						scanId={findingsScan}
						findings={run.findings}
						live={findingsLive}
						{highlight}
					/>
				{:else if loaded}
					<span class="text-xs text-muted-foreground">—</span>
				{:else}
					<Skeleton class="h-6 w-28 rounded-md" />
				{/if}
			</div>
		{/if}

		{#if targetPrefs.fits('assets')}
			<div class="{TCOL.assets} h-6 items-center">
				{#if run}
					<AssetsCell scan={run} />
				{:else if !loaded}
					<Skeleton class="h-6 w-40 rounded-md" />
				{/if}
			</div>
		{/if}

		{#if targetPrefs.fits('change')}
			<div class="{TCOL.change} h-6 items-center">
				{#if run}
					<ChangeCell {projectId} scan={run} onCompare={() => onCompare(run)} />
				{:else if !loaded}
					<Skeleton class="h-4 w-14" />
				{/if}
			</div>
		{/if}

		{#if targetPrefs.fits('organizations')}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="{TCOL.organizations} h-6 items-center" onclick={stopProp}>
				<TargetOrgPopover targetId={target.id} currentOrgs={target.organizations} />
			</div>
		{/if}

		{#if targetPrefs.fits('tags')}
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="{TCOL.tags} h-6 items-center" onclick={stopProp}>
				<TargetTagPopover targetId={target.id} currentTags={target.tags} />
			</div>
		{/if}

		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="{TCOL.actions} items-center gap-0.5" onclick={stopProp}>
			<Hint text={scanning ? 'Scanning' : 'Scan'}>
				{#snippet child(props)}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="size-7"
						aria-label="Scan {target.target_value}"
						onclick={onScan}
					>
						{#if scanning}
							<Spinner class="size-4 text-info" />
						{:else}
							<Play class="size-4" />
						{/if}
					</Button>
				{/snippet}
			</Hint>
			<Button
				variant="ghost"
				size="icon"
				class="size-7"
				aria-label={expanded ? 'Collapse target brief' : 'Expand target brief'}
				aria-expanded={expanded}
				onclick={onToggle}
			>
				<ChevronDown class="size-4 transition-transform {expanded ? 'rotate-180' : ''}" />
			</Button>
			<DropdownMenu.Root>
				<DropdownMenu.Trigger>
					{#snippet child({ props })}
						<Button {...props} variant="ghost" size="icon" class="size-7">
							<Ellipsis class="size-4" />
							<span class="sr-only">Actions for {target.target_value}</span>
						</Button>
					{/snippet}
				</DropdownMenu.Trigger>
				<DropdownMenu.Content align="end" class="w-52">
					<DropdownMenu.Item onSelect={() => goto(ROUTES.target(target.id))}>
						<ExternalLink /> Open target
					</DropdownMenu.Item>
					{#if run}
						<DropdownMenu.Item onSelect={() => goto(ROUTES.scan(run.id))}>
							<ExternalLink /> Open latest run
						</DropdownMenu.Item>
						<DropdownMenu.Item onSelect={() => onCompare(run)} disabled={!!run.is_first_scan}>
							<GitCompare /> Compare with previous
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item onSelect={onScan}><Play /> Scan</DropdownMenu.Item>
					<DropdownMenu.Item onSelect={onSchedule}
						><CalendarClock /> Schedule scan</DropdownMenu.Item
					>
					<DropdownMenu.Item onSelect={onHistory}><History /> Scan history</DropdownMenu.Item>
					<DropdownMenu.Item onSelect={startRename}><Pencil /> Rename</DropdownMenu.Item>
					<DropdownMenu.Separator />
					<DropdownMenu.Item onSelect={() => onReEnrich('whois')}>
						<RefreshCw /> Re-run WHOIS
					</DropdownMenu.Item>
					{#if canDns}
						<DropdownMenu.Item onSelect={() => onReEnrich('dns')}>
							<RefreshCw /> Re-run DNS
						</DropdownMenu.Item>
					{/if}
					{#if canBgp}
						<DropdownMenu.Item onSelect={() => onReEnrich('bgp')}>
							<RefreshCw /> Re-run BGP
						</DropdownMenu.Item>
					{/if}
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onSelect={onDelete}>
						<Trash2 /> Delete target
					</DropdownMenu.Item>
				</DropdownMenu.Content>
			</DropdownMenu.Root>
		</div>
	</div>

	{#if expanded}
		<div class="px-4 pt-1 pb-4 @xl/targets:pl-12">
			{#if run}
				<RunBrief {projectId} scan={run} {now} {onChanged} onHover={(s) => (highlight = s)} />
			{:else}
				<p class="rounded-md border bg-card px-3 py-4 text-sm text-muted-foreground">Not scanned</p>
			{/if}
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<Button size="sm" class="h-8 gap-1.5" href={ROUTES.target(target.id)}>
					<ExternalLink class="size-3.5" /> Open target
				</Button>
				{#if run}
					<Button size="sm" variant="outline" class="h-8 gap-1.5" href={ROUTES.scan(run.id)}>
						<ExternalLink class="size-3.5" /> Open latest run
					</Button>
					{#if !run.is_first_scan}
						<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={() => onCompare(run)}>
							<GitCompare class="size-3.5" /> Compare with previous
						</Button>
					{/if}
				{/if}
				<Button size="sm" variant="outline" class="h-8 gap-1.5" onclick={onScan}>
					<Play class="size-3.5" />
					{run ? 'Run again' : 'Scan'}
				</Button>
				<Button size="sm" variant="ghost" class="h-8 gap-1.5" onclick={onHistory}>
					<History class="size-3.5" /> Scan history
				</Button>
			</div>
		</div>
	{/if}
</div>
