<script lang="ts">
	import { goto } from '$app/navigation';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { useSidebar } from '$lib/components/ui/sidebar/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import LiveScanRow from '$lib/components/scans/live-scan-row.svelte';
	import Radar from '@lucide/svelte/icons/radar';
	import Play from '@lucide/svelte/icons/play';
	import Plus from '@lucide/svelte/icons/plus';
	import X from '@lucide/svelte/icons/x';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { dashboardStore } from '$lib/stores/dashboard.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { ROUTES } from '$lib/config/routes';
	import { STORAGE_KEYS } from '$lib/config/storage-keys';
	import { NOW_TICK_MS } from '$lib/constants';

	const MAX_ROWS = 3;
	const sidebar = useSidebar();

	let projectId = $derived(projectsStore.activeProject?.id);
	let collapsed = $derived(sidebar.state === 'collapsed' && !sidebar.isMobile);

	$effect(() => {
		if (projectId) dashboardStore.init(projectId);
	});

	$effect(() => {
		if (liveScans.completedTick > 0) dashboardStore.refresh();
	});

	let now = $state(Date.now());
	$effect(() => {
		if (!liveScans.hasLive) return;
		const t = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		return () => clearInterval(t);
	});

	let signals = $derived(dashboardStore.signals);
	let neverScanned = $derived(signals?.stale.never_scanned ?? 0);
	let stale = $derived(signals?.stale.stale ?? 0);
	let gap = $derived(neverScanned + stale);
	let gapKey = $derived(`${projectId}:${neverScanned}:${stale}`);

	function readDismissed(): string {
		try {
			return sessionStorage.getItem(STORAGE_KEYS.scanNudgeDismissed) ?? '';
		} catch {
			return '';
		}
	}
	let dismissedKey = $state(readDismissed());
	function dismiss() {
		dismissedKey = gapKey;
		try {
			sessionStorage.setItem(STORAGE_KEYS.scanNudgeDismissed, gapKey);
		} catch {}
	}

	type Mode = 'loading' | 'running' | 'gap' | 'empty' | 'fresh' | 'hidden';
	let mode = $derived.by((): Mode => {
		if (!projectId) return 'hidden';
		if (liveScans.hasLive) return 'running';
		if (!liveScans.hasFetched) return 'loading';
		if (!signals) return dashboardStore.signalsError ? 'fresh' : 'loading';
		if (liveScans.stats?.total === 0 && gap === 0) return 'empty';
		if (gap > 0) return dismissedKey === gapKey ? 'hidden' : 'gap';
		return 'fresh';
	});

	let visible = $derived(liveScans.scans.slice(0, MAX_ROWS));
	let overflow = $derived(liveScans.count - MAX_ROWS);
	let gapText = $derived.by(() => {
		const parts: string[] = [];
		if (neverScanned > 0) parts.push(`${neverScanned} never scanned`);
		if (stale > 0) parts.push(`${stale} not scanned in 30d`);
		return parts.join(' · ');
	});
	let lastScanLabel = $derived(
		liveScans.stats?.last_scan_at ? relativeTime(liveScans.stats.last_scan_at) : null
	);

	let launchOpen = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);
	let addTargetOpen = $state(false);

	function runScan() {
		const items = signals?.stale.items ?? [];
		launchTargetId = mode === 'gap' && items.length === 1 ? items[0].target_id : undefined;
		launchOpen = true;
	}
	function onLaunchClose() {
		launchOpen = false;
		launchTargetId = undefined;
		liveScans.refresh();
	}
	function primaryAction() {
		if (mode === 'running') goto(ROUTES.scans);
		else if (mode === 'empty') addTargetOpen = true;
		else runScan();
	}

	let collapsedTooltip = $derived.by(() => {
		if (mode === 'running')
			return `${liveScans.count} scan${liveScans.count === 1 ? '' : 's'} running`;
		if (mode === 'gap') return `${gap} target${gap === 1 ? '' : 's'} need a scan`;
		if (mode === 'empty') return 'Add target';
		return 'New scan';
	});
</script>

{#if collapsed}
	{#if mode !== 'loading'}
		<Sidebar.Menu>
			<Sidebar.MenuItem>
				<Sidebar.MenuButton
					tooltipContent={collapsedTooltip}
					onclick={primaryAction}
					class="relative"
				>
					{#if mode === 'empty'}
						<Plus />
					{:else if mode === 'running' || mode === 'gap' || mode === 'hidden'}
						<Radar class={mode === 'running' ? 'text-info' : undefined} />
					{:else}
						<Play />
					{/if}
					{#if mode === 'running'}
						<span class="absolute top-1.5 right-1.5 size-1.5 animate-pulse rounded-full bg-info"
						></span>
					{:else if mode === 'gap'}
						<span class="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-warning"></span>
					{/if}
				</Sidebar.MenuButton>
			</Sidebar.MenuItem>
		</Sidebar.Menu>
	{/if}
{:else if mode === 'loading'}
	<div class="rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-3">
		<Skeleton class="h-3 w-24" />
		<Skeleton class="mt-2 h-3 w-full" />
		<Skeleton class="mt-2.5 h-7 w-full" />
	</div>
{:else if mode === 'running'}
	<div class="rounded-lg border border-info/20 bg-info/5 p-2.5">
		<div class="flex items-center justify-between px-1">
			<span
				class="flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.08em] text-muted-foreground uppercase"
			>
				<span class="relative flex size-1.5">
					<span class="absolute inline-flex size-full animate-ping rounded-full bg-info opacity-75"
					></span>
					<span class="relative inline-flex size-1.5 rounded-full bg-info"></span>
				</span>
				Scanning
			</span>
			<span class="font-mono text-[10px] font-medium text-info tabular-nums">
				{liveScans.count} live
			</span>
		</div>
		<div class="mt-1.5 space-y-px">
			{#each visible as scan (scan.id)}
				<LiveScanRow {scan} stage={liveScans.stageFor(scan.id)} {now} />
			{/each}
		</div>
		<a
			href={ROUTES.scans}
			class="mt-1.5 inline-flex items-center gap-1 px-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
		>
			{overflow > 0 ? `+${overflow} more` : 'All scans'}
			<ArrowRight class="size-3" />
		</a>
	</div>
{:else if mode === 'gap'}
	<div class="rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-3">
		<div class="flex items-start gap-2.5">
			<div
				class="flex size-7 shrink-0 items-center justify-center rounded-md bg-warning/10 text-warning"
			>
				<Radar class="size-3.5" />
			</div>
			<div class="min-w-0 flex-1">
				<p class="text-[13px] leading-tight font-medium">Coverage gap</p>
				<p class="mt-0.5 text-[11px] leading-snug text-muted-foreground">{gapText}</p>
			</div>
			<Button
				variant="ghost"
				size="icon-sm"
				class="-mt-1 -mr-1 size-6 text-muted-foreground"
				onclick={dismiss}
				aria-label="Dismiss"
			>
				<X class="size-3" />
			</Button>
		</div>
		<Button size="sm" class="mt-2.5 h-7 w-full text-xs" onclick={runScan}>
			<Play class="size-3" />
			Run scan
		</Button>
	</div>
{:else if mode === 'empty'}
	<div class="rounded-lg border border-dashed border-sidebar-border p-3">
		<div class="flex items-start gap-2.5">
			<div
				class="flex size-7 shrink-0 items-center justify-center rounded-md bg-sidebar-accent text-muted-foreground"
			>
				<Plus class="size-3.5" />
			</div>
			<div class="min-w-0 flex-1">
				<p class="text-[13px] leading-tight font-medium">No targets yet</p>
				<p class="mt-0.5 text-[11px] leading-snug text-muted-foreground">
					Add a domain, IP or CIDR to start mapping.
				</p>
			</div>
		</div>
		<Button size="sm" class="mt-2.5 h-7 w-full text-xs" onclick={() => (addTargetOpen = true)}>
			<Plus class="size-3" />
			Add target
		</Button>
	</div>
{:else if mode === 'fresh'}
	<div
		class="flex items-center gap-2.5 rounded-lg border border-sidebar-border bg-sidebar-accent/40 py-1.5 pr-1.5 pl-3"
	>
		<CircleCheck class="size-3.5 shrink-0 text-success" />
		<div class="min-w-0 flex-1 leading-tight">
			<p class="text-[12px] font-medium">Coverage fresh</p>
			{#if lastScanLabel}
				<p class="truncate text-[10px] text-muted-foreground">Last scan {lastScanLabel}</p>
			{/if}
		</div>
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon-sm"
						class="size-7 text-muted-foreground hover:text-foreground"
						onclick={runScan}
						aria-label="New scan"
					>
						<Play class="size-3.5" />
					</Button>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content side="right">New scan</Tooltip.Content>
		</Tooltip.Root>
	</div>
{/if}

<LaunchModal bind:open={launchOpen} targetId={launchTargetId} onClose={onLaunchClose} />
<AddTargetModal bind:open={addTargetOpen} />
