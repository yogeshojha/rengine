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
	import { subdomainsApi } from '$lib/api/subdomains';
	import { httpAssetsApi, portsApi, ipsApi } from '$lib/api/scan-results';
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
	import SubdomainResultsTable from '$lib/components/scans/results/subdomain-results-table.svelte';
	import InfraCards from '$lib/components/scans/results/infra-cards.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		scanCountPills,
		durationLabel,
		isLiveStatus,
		SCAN_POLL_MS
	} from '$lib/utilities/scan-status';
	import { correlateByIp } from '$lib/utilities/scan-correlation';
	import type { ScanRead, ScanActivityRead, ScanCommandRead } from '$lib/types/scan';
	import type { SubdomainRead } from '$lib/types/subdomain';
	import type { HttpAssetRead } from '$lib/types/http-asset';
	import type { IpAddressRead } from '$lib/types/ip-address';
	import type { PortRead } from '$lib/types/port';
	import { ROUTES } from '$lib/config/routes';
	import { NOW_TICK_MS } from '$lib/constants';

	const TABS = ['overview', 'web', 'subdomains', 'infra', 'pipeline'] as const;
	type TabKey = (typeof TABS)[number];

	const scanId = $derived(page.params.id ?? '');

	let scan = $state<ScanRead | null>(null);
	let subs = $state<SubdomainRead[]>([]);
	let assets = $state<HttpAssetRead[]>([]);
	let ips = $state<IpAddressRead[]>([]);
	let ports = $state<PortRead[]>([]);
	let activities = $state<ScanActivityRead[]>([]);
	let commands = $state<ScanCommandRead[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showRescan = $state(false);
	let refreshTimer: ReturnType<typeof setTimeout> | null = null;
	let now = $state(Date.now());

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
			void 0;
		}
	}

	$effect(() => {
		if (!scan || !isLiveStatus(scan.status)) return;
		const t = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		return () => clearInterval(t);
	});

	let counters = $derived(scan ? scanCountPills(scan) : []);
	let shouldPoll = $derived(!!scan && isLiveStatus(scan.status) && !sseStore.isConnected);
	let ipGroups = $derived(correlateByIp(ips, ports, assets, subs));
	let ipGroupMap = $derived(new Map(ipGroups.map((g) => [g.ip, g])));

	let delta = $derived(
		scan && !scan.is_first_scan && (scan.new_subdomains || scan.gone_subdomains)
			? { added: scan.new_subdomains ?? 0, removed: scan.gone_subdomains ?? 0 }
			: null
	);

	async function loadAssets(projectId: string) {
		try {
			[subs, assets, ips, ports] = await Promise.all([
				subdomainsApi.listByScan(projectId, scanId, { limit: 1000 }),
				httpAssetsApi.listByScan(projectId, scanId, { limit: 1000 }),
				ipsApi.listByScan(projectId, scanId, { limit: 1000 }),
				portsApi.listByScan(projectId, scanId, { limit: 1000 })
			]);
		} catch {
			void 0;
		}
	}

	async function loadPipeline(projectId: string) {
		try {
			[activities, commands] = await Promise.all([
				scansApi.activities(scanId, projectId),
				scansApi.commands(scanId, projectId)
			]);
		} catch {
			void 0;
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
			await Promise.all([loadAssets(project.id), loadPipeline(project.id)]);
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

	let running = $derived(!!scan && (scan.status === 'running' || scan.status === 'pending'));
</script>

<div class="mx-auto w-full max-w-6xl space-y-4 p-4">
	<a
		href={ROUTES.scans}
		class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
	>
		<ArrowLeft class="h-3.5 w-3.5" />
		Scans
	</a>

	{#if loading && !scan}
		<Skeleton class="h-28 w-full" />
		<Skeleton class="h-64 w-full" />
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
				<div class="space-y-1">
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
						<RefreshCw class="h-3.5 w-3.5 {loading ? 'animate-spin' : ''}" />
						Refresh
					</Button>
					<Button size="sm" class="gap-1.5" onclick={() => (showRescan = true)}>
						<Play class="h-3.5 w-3.5" />
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
					<div
						class="rounded-md border bg-card/40 p-2.5 {c.emphasis && c.value > 0
							? 'border-destructive/40'
							: 'border-border'}"
					>
						<div
							class="text-lg font-semibold tabular-nums {c.emphasis && c.value > 0
								? 'text-destructive'
								: ''}"
						>
							{c.value}
						</div>
						<div class="flex items-center gap-1 text-xs text-muted-foreground">
							<PillIcon class="h-3 w-3" />
							{c.label}
						</div>
					</div>
				{/each}
			</div>

			{#if delta}
				<div class="mt-3 flex flex-wrap items-center gap-3 text-xs">
					{#if delta.added > 0}
						<span class="flex items-center gap-1 text-success">
							<ArrowUpRight class="h-3.5 w-3.5" />
							{delta.added} new subdomain{delta.added === 1 ? '' : 's'}
						</span>
					{/if}
					{#if delta.removed > 0}
						<span class="flex items-center gap-1 text-muted-foreground">
							<ArrowDownRight class="h-3.5 w-3.5" />
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
				<Tabs.Trigger value="web">
					Web <span class="ml-1 text-muted-foreground">{assets.length}</span>
				</Tabs.Trigger>
				<Tabs.Trigger value="subdomains">
					Subdomains <span class="ml-1 text-muted-foreground">{subs.length}</span>
				</Tabs.Trigger>
				<Tabs.Trigger value="infra">
					Infrastructure <span class="ml-1 text-muted-foreground">{ipGroups.length}</span>
				</Tabs.Trigger>
				<Tabs.Trigger value="pipeline">
					Pipeline <span class="ml-1 text-muted-foreground">{activities.length}</span>
				</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="overview" class="mt-4">
				{#if assets.length || ips.length || ports.length}
					<ScanOverview {assets} {ips} {ports} />
				{:else}
					{@render emptyTab(
						running
							? 'Scan in progress — results will appear here as assets are discovered.'
							: 'No results recorded for this scan.'
					)}
				{/if}
			</Tabs.Content>

			<Tabs.Content value="web" class="mt-4">
				{#if assets.length}
					<WebAssetsTable {assets} ipGroups={ipGroupMap} />
				{:else}
					{@render emptyTab(
						running ? 'Probing for live web services…' : 'No web services found in this scan.'
					)}
				{/if}
			</Tabs.Content>

			<Tabs.Content value="subdomains" class="mt-4">
				{#if subs.length}
					<SubdomainResultsTable subdomains={subs} />
				{:else}
					{@render emptyTab(
						running ? 'Discovering subdomains…' : 'No subdomains recorded for this scan.'
					)}
				{/if}
			</Tabs.Content>

			<Tabs.Content value="infra" class="mt-4">
				{#if ipGroups.length}
					<InfraCards groups={ipGroups} />
				{:else}
					{@render emptyTab(
						running
							? 'Resolving hosts and scanning ports…'
							: 'No IP infrastructure recorded for this scan.'
					)}
				{/if}
			</Tabs.Content>

			<Tabs.Content value="pipeline" class="mt-4 space-y-4">
				{#if activities.length}
					<ScanActivityTimeline {activities} />
				{:else}
					{@render emptyTab('No pipeline activity recorded yet.')}
				{/if}
				{#if commands.length}
					<ScanCommandLog {scanId} projectId={projectsStore.activeProject?.id ?? ''} {commands} />
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
