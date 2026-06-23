<script lang="ts">
	import { page } from '$app/state';
	import { onDestroy, untrack } from 'svelte';
	import { ArrowLeft, RefreshCw, Play, Network, Activity, Terminal } from 'lucide-svelte';

	import { scansApi } from '$lib/api/scans';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ScanEvent } from '$lib/types/sse';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Empty from '$lib/components/ui/empty';
	import SubdomainTable from '$lib/components/scans/subdomain-table.svelte';
	import ScanActivityTimeline from '$lib/components/scans/scan-activity-timeline.svelte';
	import ScanCommandLog from '$lib/components/scans/scan-command-log.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import {
		SCAN_STATUS_LABEL,
		scanStatusVariant,
		scanStatusIcon,
		scanCountPills,
		durationLabel,
		isLiveStatus,
		SCAN_POLL_MS
	} from '$lib/utilities/scan-status';
	import type { ScanRead, ScanActivityRead, ScanCommandRead } from '$lib/types/scan';
	import type { SubdomainRead } from '$lib/types/subdomain';

	const scanId = $derived(page.params.id ?? '');

	let scan = $state<ScanRead | null>(null);
	let subs = $state<SubdomainRead[]>([]);
	let activities = $state<ScanActivityRead[]>([]);
	let commands = $state<ScanCommandRead[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showRescan = $state(false);
	let refreshTimer: ReturnType<typeof setTimeout> | null = null;
	let now = $state(Date.now());

	$effect(() => {
		if (!scan || !isLiveStatus(scan.status)) return;
		const t = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(t);
	});

	let counters = $derived(scan ? scanCountPills(scan) : []);

	let shouldPoll = $derived(!!scan && isLiveStatus(scan.status) && !sseStore.isConnected);

	let subRows = $derived(
		subs.map((s) => ({
			name: s.name,
			sources: s.sources,
			resolved_ips: s.resolved_ips,
			is_active: s.is_active,
			is_wildcard: s.is_wildcard,
			is_excluded: s.is_excluded,
			last_seen: s.discovered_at
		}))
	);

	async function loadSubs(projectId: string) {
		try {
			subs = await subdomainsApi.listByScan(projectId, scanId, { limit: 1000 });
		} catch {
			// non-fatal: results table just stays empty
		}
	}

	async function loadPipeline(projectId: string) {
		try {
			[activities, commands] = await Promise.all([
				scansApi.activities(scanId, projectId),
				scansApi.commands(scanId, projectId)
			]);
		} catch {
			// non-fatal: pipeline panels stay empty
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
			await Promise.all([loadSubs(project.id), loadPipeline(project.id)]);
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

	// scan events ride the project channel; filter to this scan
	$effect(() => {
		const project = projectsStore.activeProject;
		const id = scanId;
		if (!project || !id) return;
		return sseStore.on<ScanEvent>(SSEChannel.project(project.id), SSEEventType.SCAN, (data) => {
			if (data.scan_id === id) scheduleRefresh();
		});
	});

	// fallback poll only when SSE is unavailable
	$effect(() => {
		if (!shouldPoll) return;
		const t = setInterval(() => load(true), SCAN_POLL_MS);
		return () => clearInterval(t);
	});

	onDestroy(() => {
		if (refreshTimer) clearTimeout(refreshTimer);
		if (scanId) breadcrumbStore.remove(scanId);
	});
</script>

<div class="mx-auto w-full max-w-5xl space-y-4 p-4">
	<a
		href="/scans"
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
		{@const StatusIcon = scanStatusIcon(scan.status)}
		<div class="rounded-lg border border-border p-4">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="space-y-1">
					<div class="flex items-center gap-2">
						<h1 class="font-mono text-lg">{scan.execution_config.target_value}</h1>
						<Badge variant={scanStatusVariant(scan.status)} class="gap-1 font-normal">
							<StatusIcon class="h-3 w-3 {scan.status === 'running' ? 'animate-spin' : ''}" />
							{SCAN_STATUS_LABEL[scan.status]}
						</Badge>
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

			<div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
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
		</div>

		{#if activities.length}
			<div class="space-y-2">
				<div class="flex items-center gap-2">
					<Activity class="h-4 w-4 text-muted-foreground" />
					<h2 class="text-sm font-medium">Pipeline</h2>
					<span class="text-xs text-muted-foreground">({activities.length})</span>
				</div>
				<ScanActivityTimeline {activities} />
			</div>
		{/if}

		{#if commands.length}
			<div class="space-y-2">
				<div class="flex items-center gap-2">
					<Terminal class="h-4 w-4 text-muted-foreground" />
					<h2 class="text-sm font-medium">Commands</h2>
					<span class="text-xs text-muted-foreground">({commands.length})</span>
				</div>
				<ScanCommandLog {scanId} projectId={projectsStore.activeProject?.id ?? ''} {commands} />
			</div>
		{/if}

		<div class="space-y-2">
			<div class="flex items-center gap-2">
				<Network class="h-4 w-4 text-muted-foreground" />
				<h2 class="text-sm font-medium">Subdomains</h2>
				<span class="text-xs text-muted-foreground">({subs.length})</span>
			</div>
			{#if subRows.length === 0}
				<p
					class="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground"
				>
					{scan.status === 'running' || scan.status === 'pending'
						? 'Scan in progress — subdomains will appear as they are discovered.'
						: 'No subdomains recorded for this scan.'}
				</p>
			{:else}
				<SubdomainTable rows={subRows} />
			{/if}
		</div>
	{/if}
</div>

{#if scan}
	<LaunchModal
		bind:open={showRescan}
		targetId={scan.target_id}
		onClose={() => (showRescan = false)}
	/>
{/if}
