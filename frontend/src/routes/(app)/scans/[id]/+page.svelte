<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { onDestroy, untrack } from 'svelte';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import Play from '@lucide/svelte/icons/play';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ArrowDownRight from '@lucide/svelte/icons/arrow-down-right';

	import { scansApi } from '$lib/api/scans';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ScanEvent } from '$lib/types/sse';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tabs from '$lib/components/ui/tabs';
	import ScanStatusBadge from '@/components/scan-status-badge.svelte';
	import ScanActivityTimeline from '$lib/components/scans/scan-activity-timeline.svelte';
	import ScanCommandLog from '$lib/components/scans/scan-command-log.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import ScanOverview from '$lib/components/scans/results/scan-overview.svelte';
	import WebAssetsTable from '$lib/components/scans/results/web-assets-table.svelte';
	import IpsTable from '$lib/components/scans/results/ips-table.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		scanCountPills,
		durationLabel,
		isLiveStatus,
		SCAN_POLL_MS
	} from '$lib/utilities/scan-status';
	import { emptyQuery, type WebAssetQuery } from '$lib/utilities/scan-insights';
	import type { ScanRead, ScanActivityRead, ScanCommandRead } from '$lib/types/scan';
	import { ROUTES } from '$lib/config/routes';
	import { NOW_TICK_MS } from '$lib/constants';

	const TABS = ['overview', 'web-assets', 'ips', 'pipeline'] as const;
	type TabKey = (typeof TABS)[number];

	const scanId = $derived(page.params.id ?? '');

	let scan = $state<ScanRead | null>(null);
	let activities = $state<ScanActivityRead[]>([]);
	let commands = $state<ScanCommandRead[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showRescan = $state(false);
	let refreshTimer: ReturnType<typeof setTimeout> | null = null;
	let now = $state(Date.now());
	let webQuery = $state<WebAssetQuery>(emptyQuery());

	const initialTab = page.url.searchParams.get('tab');
	let activeTab = $state<TabKey>(
		initialTab && (TABS as readonly string[]).includes(initialTab)
			? (initialTab as TabKey)
			: 'overview'
	);

	function setTab(v: string) {
		activeTab = v as TabKey;
		try {
			replaceState(`?tab=${v}`, page.state);
		} catch {
			// ignore — URL state is best-effort
		}
	}

	function applyFilter(search: string) {
		webQuery = { ...emptyQuery(), search };
		setTab('web-assets');
	}

	function pillTab(key: string): TabKey | null {
		if (/sub|web|http|asset/.test(key)) return 'web-assets';
		if (/ip|port/.test(key)) return 'ips';
		return null;
	}

	$effect(() => {
		if (!scan || !isLiveStatus(scan.status)) return;
		const t = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		return () => clearInterval(t);
	});

	let counters = $derived(scan ? scanCountPills(scan) : []);
	let shouldPoll = $derived(!!scan && isLiveStatus(scan.status) && !sseStore.isConnected);

	let delta = $derived(
		scan && !scan.is_first_scan && (scan.new_subdomains || scan.gone_subdomains)
			? { added: scan.new_subdomains ?? 0, removed: scan.gone_subdomains ?? 0 }
			: null
	);

	let lastScanId = '';
	$effect(() => {
		if (scanId && scanId !== lastScanId) {
			lastScanId = scanId;
			untrack(() => (webQuery = emptyQuery()));
		}
	});

	async function loadPipeline(projectId: string) {
		try {
			[activities, commands] = await Promise.all([
				scansApi.activities(scanId, projectId),
				scansApi.commands(scanId, projectId)
			]);
		} catch {
			// pipeline is supplementary — leave prior values on failure
		}
	}

	async function load(silent = false) {
		const project = projectsStore.activeProject;
		if (!project || !scanId) return;
		if (!silent) loading = true;
		error = null;
		try {
			scan = await scansApi.get(scanId, project.id);
			if (!silent) breadcrumbStore.set(scanId, `${scan.execution_config.target_value} scan`);
			await loadPipeline(project.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load scan';
		} finally {
			if (!silent) loading = false;
		}
	}

	function scheduleRefresh() {
		if (refreshTimer) return;
		refreshTimer = setTimeout(() => {
			refreshTimer = null;
			load(true);
		}, 600);
	}

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = scanId;
		if (project && id) untrack(() => load());
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = scanId;
		if (!project || !id) return;
		return sseStore.on<ScanEvent>(SSEChannel.project(project.id), SSEEventType.SCAN, (data) => {
			if (data.scan_id === id) scheduleRefresh();
		});
	});

	$effect(() => {
		if (!shouldPoll) return;
		const t = setInterval(() => load(true), SCAN_POLL_MS);
		return () => clearInterval(t);
	});

	onDestroy(() => {
		if (refreshTimer) clearTimeout(refreshTimer);
		if (scanId) breadcrumbStore.remove(scanId);
	});

	let projectId = $derived(projectsStore.activeProject?.id ?? '');
</script>

<div class="flex w-full flex-col gap-4 px-4 py-4 md:px-6">
	<a
		href={ROUTES.scans}
		class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
	>
		<ArrowLeft class="size-3.5" />
		Scans
	</a>

	{#if loading && !scan}
		<Skeleton class="h-28 w-full" />
		<Skeleton class="h-9 w-80" />
		<Skeleton class="h-96 w-full" />
	{:else if error}
		<Empty.Root class="rounded-lg border border-dashed py-20">
			<Empty.Header>
				<Empty.Title class="text-sm">Could not load scan</Empty.Title>
				<Empty.Description>{error}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button size="sm" variant="outline" onclick={() => load()}>Retry</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if scan}
		<div class="rounded-lg border border-border p-4">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="flex flex-col gap-1">
					<div class="flex items-center gap-2">
						<h1 class="font-mono text-lg">{scan.execution_config.target_value}</h1>
						<ScanStatusBadge status={scan.status} />
					</div>
					<p class="text-sm text-muted-foreground">
						{scan.engine_name} · {scan.context_name ?? 'engine defaults'}
					</p>
				</div>
				<div class="flex items-center gap-2">
					<Button variant="outline" size="sm" class="gap-1.5" onclick={() => load()}>
						<RefreshCw class="size-3.5 {loading ? 'animate-spin' : ''}" />
						Refresh
					</Button>
					<Button size="sm" class="gap-1.5" onclick={() => (showRescan = true)}>
						<Play class="size-3.5" />
						Re-scan
					</Button>
				</div>
			</div>

			<div class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
				<span>Started {scan.started_at ? relativeTime(scan.started_at) : '—'}</span>
				<span>Duration {durationLabel(scan, now)}</span>
				<span>Created {relativeTime(scan.created_at)}</span>
				{#if scan.completed_at}<span>Finished {relativeTime(scan.completed_at)}</span>{/if}
			</div>

			{#if scan.error}
				<p
					class="mt-3 rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive"
				>
					{scan.error}
				</p>
			{/if}

			<div class="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-6">
				{#each counters as c (c.key)}
					{@const PillIcon = c.icon}
					{@const tab = pillTab(c.key)}
					{#if tab}
						<button
							type="button"
							class="rounded-md border bg-card/40 p-2.5 text-left hover:border-foreground/30 border-border"
							onclick={() => setTab(tab)}
						>
							<div class="text-lg font-semibold tabular-nums">
								{c.value.toLocaleString()}
							</div>
							<div class="flex items-center gap-1 text-xs text-muted-foreground">
								<PillIcon class="size-3" />
								{c.label}
							</div>
						</button>
					{:else}
						<div class="rounded-md border bg-card/40 p-2.5 border-border">
							<div class="text-lg font-semibold tabular-nums">
								{c.value.toLocaleString()}
							</div>
							<div class="flex items-center gap-1 text-xs text-muted-foreground">
								<PillIcon class="size-3" />
								{c.label}
							</div>
						</div>
					{/if}
				{/each}
			</div>

			{#if delta}
				<div class="mt-3 flex flex-wrap items-center gap-3 text-xs">
					{#if delta.added > 0}
						<span class="flex items-center gap-1 text-success">
							<ArrowUpRight class="size-3.5" />
							{delta.added} new subdomain{delta.added === 1 ? '' : 's'}
						</span>
					{/if}
					{#if delta.removed > 0}
						<span class="flex items-center gap-1 text-muted-foreground">
							<ArrowDownRight class="size-3.5" />
							{delta.removed} retired
						</span>
					{/if}
					<span class="text-muted-foreground">since previous scan</span>
				</div>
			{/if}
		</div>

		<Tabs.Root value={activeTab} onValueChange={setTab}>
			<Tabs.List>
				<Tabs.Trigger value="overview">Overview</Tabs.Trigger>
				<Tabs.Trigger value="web-assets">
					Web Assets <span class="ml-1 text-muted-foreground">{scan.subdomains_found}</span>
				</Tabs.Trigger>
				<Tabs.Trigger value="ips">
					IPs <span class="ml-1 text-muted-foreground">{scan.ips_found}</span>
				</Tabs.Trigger>
				<Tabs.Trigger value="pipeline">
					Pipeline <span class="ml-1 text-muted-foreground">{activities.length}</span>
				</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="overview" class="mt-4">
				{#key scan.id}
					<ScanOverview
						{scan}
						scanId={scan.id}
						{projectId}
						active={activeTab === 'overview'}
						onFilter={applyFilter}
					/>
				{/key}
			</Tabs.Content>

			<Tabs.Content value="web-assets" class="mt-4">
				{#key scan.id}
					<WebAssetsTable
						scanId={scan.id}
						{projectId}
						active={activeTab === 'web-assets'}
						bind:query={webQuery}
					/>
				{/key}
			</Tabs.Content>

			<Tabs.Content value="ips" class="mt-4">
				{#key scan.id}
					<IpsTable scanId={scan.id} {projectId} active={activeTab === 'ips'} />
				{/key}
			</Tabs.Content>

			<Tabs.Content value="pipeline" class="mt-4 space-y-4">
				{#if activities.length}
					<ScanActivityTimeline {activities} />
				{:else}
					{@render emptyTab('No pipeline activity recorded yet.')}
				{/if}
				{#if commands.length}
					<ScanCommandLog {scanId} {projectId} {commands} />
				{/if}
			</Tabs.Content>
		</Tabs.Root>
	{/if}
</div>

{#snippet emptyTab(message: string)}
	<p
		class="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground"
	>
		{message}
	</p>
{/snippet}

{#if scan}
	<LaunchModal
		bind:open={showRescan}
		targetId={scan.target_id}
		onClose={() => (showRescan = false)}
	/>
{/if}
