<script lang="ts">
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onDestroy, untrack } from 'svelte';
	import { SvelteURLSearchParams } from 'svelte/reactivity';
	import { toast } from 'svelte-sonner';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
	import FileText from '@lucide/svelte/icons/file-text';
	import Router from '@lucide/svelte/icons/router';
	import Network from '@lucide/svelte/icons/network';

	import { targetsApi } from '$lib/api/targets';
	import { scansApi } from '$lib/api/scans';
	import { whoisApi } from '$lib/api/whois';
	import { subdomainsApi } from '$lib/api/subdomains';
	import { ipsApi } from '$lib/api/scan-results';
	import { usersApi } from '$lib/api/users';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { activityScope } from '$lib/stores/activity-scope.svelte';
	import { TargetType } from '$lib/types/target';
	import type { Target } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import type { TargetSummaryRead } from '$lib/types/target-summary';
	import type { ScanRead, ScanStatus } from '$lib/types/scan';
	import type { WhoisCorrelationResult } from '$lib/types/whois';
	import type { RelatedDomain } from '$lib/types/asset-query';
	import type { HostingFlow } from '$lib/types/hosting-flow';
	import type { InsightTally } from '$lib/utilities/scan-insights';
	import { Button } from '$lib/components/ui/button';
	import * as Empty from '$lib/components/ui/empty';
	import * as Tabs from '$lib/components/ui/tabs';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Kbd } from '$lib/components/ui/kbd';
	import { Spinner } from '$lib/components/ui/spinner';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import TargetHeader from '$lib/components/targets/target-detail/target-header.svelte';
	import TargetHeaderSkeleton from '$lib/components/targets/target-detail/target-header-skeleton.svelte';
	import SurfaceStrip from '$lib/components/targets/target-detail/overview/surface-strip.svelte';
	import AttentionPanel from '$lib/components/targets/target-detail/overview/attention-panel.svelte';
	import HostingSection from '$lib/components/targets/target-detail/overview/hosting-section.svelte';
	import ActivityTimeline from '$lib/components/targets/target-detail/overview/activity-timeline.svelte';
	import RelatedPanel from '$lib/components/targets/target-detail/overview/related-panel.svelte';
	import Rail from '$lib/components/targets/target-detail/overview/rail.svelte';
	import { buildTargetIntel } from '$lib/components/targets/target-detail/overview/derive';
	import TargetWebAssets from '$lib/components/targets/target-detail/target-web-assets.svelte';
	import DnsTab from '$lib/components/targets/target-detail/dns/dns-tab.svelte';
	import WhoisTab from '$lib/components/targets/target-detail/whois/whois-tab.svelte';
	import BgpTab from '$lib/components/targets/target-detail/bgp/bgp-tab.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { SURFACE, SurfaceDimension } from '$lib/config/surface';
	import type { IconComponent } from '$lib/config/icons';
	import { NOW_TICK_MS } from '$lib/constants';
	import { isLiveStatus } from '$lib/utilities/scan-status';
	import { downloadBlob } from '$lib/utilities/download';

	const TABS = ['overview', 'web-assets', 'dns', 'whois', 'bgp'] as const;
	type TabKey = (typeof TABS)[number];
	const TAB_DEFS: Record<TabKey, { label: string; icon: IconComponent }> = {
		overview: { label: 'Overview', icon: LayoutDashboard },
		'web-assets': {
			label: SURFACE[SurfaceDimension.WEB_ASSETS].label,
			icon: SURFACE[SurfaceDimension.WEB_ASSETS].icon
		},
		dns: { label: 'DNS', icon: Network },
		whois: { label: 'WHOIS', icon: FileText },
		bgp: { label: 'BGP', icon: Router }
	};
	const LEGACY_TABS: Record<string, TabKey> = {
		summary: 'overview',
		intelligence: 'whois',
		scans: 'overview'
	};
	const ENRICHMENT_POLL_MS = 2500;
	const MAX_ENRICHMENT_POLLS = 30;
	const HISTORY_SIZE = 12;
	const DNS_TYPES = [TargetType.DOMAIN, TargetType.URL];
	const BGP_TYPES = [TargetType.IP, TargetType.IP_RANGE, TargetType.ASN];

	const targetId = $derived(page.params.id ?? '');

	let target = $state<Target | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let showLaunchModal = $state(false);
	let cancelOpen = $state(false);
	let cancelling = $state(false);

	let detail = $state<TargetDetailRead | null>(null);
	let detailLoading = $state(true);
	let detailError = $state<string | null>(null);
	let summary = $state<TargetSummaryRead | null>(null);
	let summaryLoading = $state(true);
	let history = $state<ScanRead[]>([]);
	let historyLoaded = $state(false);
	let correlations = $state<WhoisCorrelationResult[]>([]);
	let relatedDomains = $state<RelatedDomain[]>([]);
	let relatedLoading = $state(true);
	let geography = $state<InsightTally[]>([]);
	let geoReady = $state(false);
	let creator = $state<string | null>(null);
	let refreshing = $state<Record<string, boolean>>({});
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let tabsHeight = $state(0);
	let headerEl = $state<HTMLElement | null>(null);
	let condensed = $state(false);
	let now = $state(Date.now());

	let showDns = $derived(!!target && DNS_TYPES.includes(target.target_type));
	let showBgp = $derived(!!target && BGP_TYPES.includes(target.target_type));
	let whoisStatus = $derived(detail?.whois_status ?? target?.whois_status ?? TaskStatus.PENDING);
	let dnsStatus = $derived(detail?.dns_status ?? target?.dns_status ?? TaskStatus.PENDING);
	let bgpStatus = $derived(detail?.bgp_status ?? target?.bgp_status ?? TaskStatus.PENDING);
	let intel = $derived(target ? buildTargetIntel(target, detail) : { rail: [], checks: [] });
	let latest = $derived(summary?.latest_scan ?? null);
	let live = $derived(!!latest && isLiveStatus(latest.status as ScanStatus));
	let run = $derived(live && latest ? liveScans.runFor(latest.id) : undefined);
	let dnsRecords = $derived(
		(detail?.dns?.records ?? []).filter((r) => r.record_type !== 'CDN').length
	);
	let webScanId = $derived(
		summary?.surface.find((m) => m.key === SurfaceDimension.WEB_ASSETS)?.scan_id ?? null
	);
	let ipsScanId = $derived(
		summary?.surface.find((m) => m.key === SurfaceDimension.IPS)?.scan_id ?? null
	);
	let tabCounts = $derived<Partial<Record<TabKey, number>>>({
		'web-assets': summary?.inventory_total,
		dns: detail?.dns ? dnsRecords : undefined,
		bgp: detail?.bgp?.announced_prefixes.length || undefined
	});
	let bgpHasData = $derived(
		!!detail?.bgp &&
			(!!detail.bgp.as_overview ||
				detail.bgp.announced_prefixes.length > 0 ||
				detail.bgp.network_info.length > 0 ||
				detail.bgp.prefix_overview.length > 0)
	);
	const inFlight = (s: TaskStatus) => s === TaskStatus.PENDING || s === TaskStatus.QUERYING;
	// a tab earns its place with data, or while its lookup is still running
	let tabs = $derived(
		TABS.filter((t) => {
			switch (t) {
				case 'web-assets':
					return summaryLoading || live || (summary?.inventory_total ?? 0) > 0;
				case 'dns':
					return showDns && (detailLoading || dnsRecords > 0 || inFlight(dnsStatus));
				case 'whois':
					return detailLoading || !!detail?.whois || inFlight(whoisStatus);
				case 'bgp':
					return showBgp && (detailLoading || bgpHasData || inFlight(bgpStatus));
				default:
					return true;
			}
		})
	);
	let enrichedAt = $derived.by(() => {
		if (!target) return null;
		const times = [
			target.dns_status === TaskStatus.SUCCESS ? target.dns?.queried_at : null,
			target.whois_status === TaskStatus.SUCCESS ? target.whois?.queried_at : null,
			target.bgp_status === TaskStatus.SUCCESS ? target.bgp?.queried_at : null
		]
			.filter((x): x is string => !!x)
			.map((x) => new Date(x).getTime());
		return times.length ? new Date(Math.max(...times)).toISOString() : null;
	});

	function resolveTab(raw: string | null): TabKey {
		if (!raw) return 'overview';
		const key = (LEGACY_TABS[raw] ?? raw) as TabKey;
		return (TABS as readonly string[]).includes(key) ? key : 'overview';
	}
	let activeTab = $state<TabKey>(resolveTab(page.url.searchParams.get('tab')));

	$effect(() => {
		if (target && !detailLoading && !summaryLoading && !tabs.includes(activeTab))
			setTab('overview');
	});

	function setTab(value: string) {
		if (!value) return;
		activeTab = value as TabKey;
		if (!browser) return;
		const params = new SvelteURLSearchParams(untrack(() => page.url.searchParams));
		if (value === 'overview') params.delete('tab');
		else params.set('tab', value);
		const query = params.toString();
		try {
			replaceState(query ? `?${query}` : location.pathname, {});
		} catch {
			// history is unavailable during hydration
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const t = e.target as HTMLElement | null;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
		const n = Number(e.key);
		if (n >= 1 && n <= tabs.length) setTab(tabs[n - 1]);
	}

	async function fetchTarget() {
		isLoading = true;
		error = null;
		try {
			target = await targetsApi.get(targetId);
			breadcrumbStore.set(targetId, target.target_value);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load target';
		} finally {
			isLoading = false;
		}
	}

	async function fetchDetail(silent = false) {
		if (!silent) detailLoading = true;
		try {
			detail = await targetsApi.getDetail(targetId);
			detailError = null;
		} catch (e) {
			detailError = e instanceof Error ? e.message : 'Failed to load enrichment details';
		} finally {
			if (!silent) detailLoading = false;
		}
	}

	async function fetchSummary(silent = false) {
		const project = projectsStore.activeProject;
		if (!project) return;
		if (!silent) summaryLoading = true;
		try {
			summary = await targetsApi.getSummary(targetId, project.id);
		} catch {
			summary = null;
		} finally {
			if (!silent) summaryLoading = false;
		}
	}

	async function fetchHistory() {
		const project = projectsStore.activeProject;
		if (!project) return;
		try {
			const res = await scansApi.list(project.id, {
				target_id: targetId,
				size: HISTORY_SIZE,
				sort_by: 'started',
				sort_dir: 'desc',
				include_focused: true
			});
			history = res.items;
		} catch {
			history = [];
		} finally {
			historyLoaded = true;
		}
	}

	async function fetchCorrelations() {
		try {
			correlations = await whoisApi.getTargetCorrelations(targetId);
		} catch {
			correlations = [];
		}
	}

	let relatedFor: string | null = null;
	async function fetchRelated(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || relatedFor === scanId) return;
		relatedFor = scanId;
		try {
			const res = await subdomainsApi.relatedDomains(project.id, scanId);
			relatedDomains = res.domains;
		} catch {
			relatedDomains = [];
		} finally {
			relatedLoading = false;
		}
	}

	let hostingFlow = $state<HostingFlow | null>(null);
	let hostingFor: string | null = null;
	async function fetchHostingFlow(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || hostingFor === scanId) return;
		hostingFor = scanId;
		try {
			hostingFlow = await subdomainsApi.hostingFlow(project.id, scanId);
		} catch {
			hostingFlow = null;
		}
	}
	function pickHosting(query: string) {
		if (!webScanId) return;
		const spec = SURFACE[SurfaceDimension.WEB_ASSETS];
		goto(ROUTES.scanTab(webScanId, spec.tab, { [spec.queryParam]: query }));
	}

	let geoFor: string | null = null;
	async function fetchGeography(scanId: string) {
		const project = projectsStore.activeProject;
		if (!project || geoFor === scanId) return;
		geoFor = scanId;
		try {
			const facets = await ipsApi.facets(project.id, scanId);
			geography = facets.country
				.filter((f) => f.value)
				.map((f) => ({ name: f.value, count: f.count }));
		} catch {
			geography = [];
		} finally {
			geoReady = true;
		}
	}
	let geoTotal = $derived(geography.reduce((n, t) => n + t.count, 0));
	function pickCountry(code: string) {
		if (!ipsScanId) return;
		const spec = SURFACE[SurfaceDimension.IPS];
		goto(
			ROUTES.scanTab(
				ipsScanId,
				spec.tab,
				code ? { [spec.queryParam]: `country:${code}` } : undefined
			)
		);
	}

	function hasPendingEnrichment(): boolean {
		const inFlight = (s: TaskStatus) => s === TaskStatus.PENDING || s === TaskStatus.QUERYING;
		if (inFlight(whoisStatus)) return true;
		if (showDns && inFlight(dnsStatus)) return true;
		if (showBgp && inFlight(bgpStatus)) return true;
		return false;
	}

	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	}

	function startPolling() {
		stopPolling();
		let attempts = 0;
		pollTimer = setInterval(async () => {
			attempts += 1;
			await Promise.all([fetchDetail(true), fetchTarget()]);
			if (!hasPendingEnrichment() || attempts >= MAX_ENRICHMENT_POLLS) {
				stopPolling();
				fetchCorrelations();
			}
		}, ENRICHMENT_POLL_MS);
	}

	function refreshAll(silent = true) {
		fetchSummary(silent);
		fetchHistory();
	}

	$effect(() => {
		if (targetId) {
			fetchTarget();
			fetchDetail();
			fetchCorrelations();
		}
		activityScope.targetId = targetId;
		return () => activityScope.clear();
	});

	$effect(() => {
		if (target && untrack(hasPendingEnrichment) && !pollTimer) untrack(startPolling);
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const id = targetId;
		if (project && id) untrack(() => refreshAll(false));
	});

	$effect(() => {
		if (liveScans.completedTick > 0) untrack(() => refreshAll());
	});

	$effect(() => {
		if (!live) return;
		const tick = setInterval(() => (now = Date.now()), NOW_TICK_MS);
		const poll = setInterval(() => refreshAll(), 15_000);
		return () => {
			clearInterval(tick);
			clearInterval(poll);
		};
	});

	$effect(() => {
		const scanId = webScanId;
		if (scanId)
			untrack(() => {
				fetchRelated(scanId);
				fetchHostingFlow(scanId);
			});
		else if (!summaryLoading) relatedLoading = false;
	});

	$effect(() => {
		const scanId = ipsScanId;
		if (scanId) untrack(() => fetchGeography(scanId));
		else if (!summaryLoading) geoReady = true;
	});

	$effect(() => {
		const id = target?.created_by;
		creator = null;
		if (!id) return;
		usersApi
			.getSummary(id)
			.then((u) => {
				if (target?.created_by === id) creator = u.username;
			})
			.catch(() => {});
	});

	$effect(() => {
		const el = headerEl;
		if (!el) return;
		const io = new IntersectionObserver(([entry]) => (condensed = !entry.isIntersecting), {
			threshold: 0
		});
		io.observe(el);
		return () => io.disconnect();
	});

	onDestroy(() => {
		stopPolling();
		if (targetId) breadcrumbStore.remove(targetId);
	});

	function handleScan() {
		if (!target) return;
		showLaunchModal = true;
	}

	async function confirmCancel() {
		if (!latest) return;
		cancelling = true;
		const ok = await liveScans.cancel(latest);
		cancelling = false;
		cancelOpen = false;
		if (ok) {
			toast.success('Scan cancelled');
			refreshAll();
		} else toast.error('Could not cancel the scan');
	}

	async function handleRefreshEnrichment() {
		if (!target) return;
		const requests: Promise<unknown>[] = [targetsApi.refreshWhois(target.id)];
		if (showDns) requests.push(targetsApi.refreshDns(target.id));
		if (showBgp) requests.push(targetsApi.refreshBgp(target.id));
		const results = await Promise.allSettled(requests);
		const failed = results.filter((r) => r.status === 'rejected').length;
		if (failed === results.length) toast.error('Enrichment refresh failed');
		else if (failed > 0) toast.error(`${failed} of ${results.length} lookups failed to start`);
		else toast.success('Enrichment refresh started');
		await fetchTarget();
		startPolling();
	}

	async function refreshOne(kind: 'dns' | 'whois' | 'bgp') {
		if (!target) return;
		const call = {
			dns: targetsApi.refreshDns,
			whois: targetsApi.refreshWhois,
			bgp: targetsApi.refreshBgp
		}[kind];
		refreshing = { ...refreshing, [kind]: true };
		try {
			await call(target.id);
			toast.success(`${kind.toUpperCase()} refresh started`);
			await fetchTarget();
			startPolling();
		} catch {
			toast.error(`${kind.toUpperCase()} refresh failed`);
		} finally {
			refreshing = { ...refreshing, [kind]: false };
		}
	}

	function patchTarget(patch: Partial<Target>) {
		if (target) target = { ...target, ...patch };
	}

	const fileName = (ext: string) =>
		`${(target?.target_value ?? 'target').replace(/[^a-z0-9.-]+/gi, '_')}.${ext}`;

	function handleExportJson() {
		if (!target) return;
		downloadBlob(
			fileName('json'),
			JSON.stringify({ target, detail, summary, scans: history, correlations }, null, 2),
			'application/json'
		);
		toast.success('Exported target as JSON');
	}

	function handleExportCsv() {
		if (!target) return;
		const rows: [string, string][] = [
			['target_value', target.target_value],
			['target_type', target.target_type],
			['display_name', target.display_name ?? ''],
			['whois_status', target.whois_status],
			['dns_status', target.dns_status],
			['bgp_status', target.bgp_status],
			['organizations', target.organizations.map((o) => o.name).join('; ')],
			['tags', target.tags.map((t) => t.name).join('; ')],
			['scans', String(summary?.scans_total ?? 0)],
			...(summary?.surface ?? []).map(
				(m) =>
					[m.label.toLowerCase().replace(/\s+/g, '_'), String(m.value ?? '')] as [string, string]
			),
			...intel.rail.flatMap((g) =>
				g.rows.map(
					(r) =>
						[`${g.key}_${r.label.toLowerCase().replace(/\s+/g, '_')}`, r.value] as [string, string]
				)
			),
			['created_at', target.created_at],
			['updated_at', target.updated_at]
		];
		const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
		const csv = ['field,value', ...rows.map(([k, v]) => `${esc(k)},${esc(v)}`)].join('\n');
		downloadBlob(fileName('csv'), csv, 'text/csv');
		toast.success('Exported target as CSV');
	}

	async function confirmDelete() {
		if (!target) return;
		isDeleting = true;
		try {
			await targetsApi.delete(target.id);
			toast.success(`Target ${target.target_value} deleted`);
			showDeleteDialog = false;
			goto(ROUTES.targets);
		} catch {
			toast.error('Failed to delete target');
		} finally {
			isDeleting = false;
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

<div class="flex w-full flex-col gap-4 px-4 py-4 md:px-6">
	<a
		href={ROUTES.targets}
		class="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
	>
		<ArrowLeft class="size-3.5" />
		Targets
	</a>

	{#if isLoading && !target}
		<TargetHeaderSkeleton />
	{:else if error}
		<Empty.Root class="min-h-[50vh] border-none">
			<Empty.Header>
				<Empty.Media
					variant="icon"
					class="size-16 rounded-full bg-destructive/10 text-destructive [&_svg:not([class*='size-'])]:size-8"
				>
					<TriangleAlert />
				</Empty.Media>
				<Empty.Title>Target not found</Empty.Title>
				<Empty.Description class="max-w-md">{error}</Empty.Description>
			</Empty.Header>
			<Empty.Content>
				<Button variant="outline" class="gap-2" onclick={() => goto(ROUTES.targets)}>
					<ChevronLeft class="size-4" />
					Back to targets
				</Button>
			</Empty.Content>
		</Empty.Root>
	{:else if target}
		<div bind:this={headerEl}>
			<TargetHeader
				{target}
				{creator}
				{live}
				onScan={handleScan}
				onCancel={() => (cancelOpen = true)}
				onRefreshEnrichment={handleRefreshEnrichment}
				onExportJson={handleExportJson}
				onExportCsv={handleExportCsv}
				onDelete={() => (showDeleteDialog = true)}
				onChange={patchTarget}
			/>
		</div>

		{#if detailError && !detailLoading}
			<div
				class="flex items-center justify-between gap-3 rounded-md border border-destructive/40 bg-destructive/5 px-4 py-3"
			>
				<p class="text-sm text-destructive">
					Enrichment details could not be loaded. {detailError}
				</p>
				<Button variant="outline" size="sm" onclick={() => fetchDetail()}>Retry</Button>
			</div>
		{/if}

		<Tabs.Root value={activeTab} onValueChange={setTab} style="--target-tabs-h: {tabsHeight}px">
			<div
				bind:clientHeight={tabsHeight}
				class="sticky top-0 z-30 -mx-4 border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:-mx-6 md:px-6"
			>
				<div class="flex items-center gap-4">
					{#if condensed}
						<div
							class="hidden shrink-0 items-center gap-2 border-r border-border py-2 pr-4 sm:flex"
						>
							<span class="font-mono text-sm">{target.target_value}</span>
							{#if live}
								<Spinner class="size-3.5 text-info" />
							{/if}
						</div>
					{/if}
					<Tabs.List class="h-auto w-full justify-start gap-0 rounded-none bg-transparent p-0">
						{#each tabs as key, i (key)}
							{@const t = TAB_DEFS[key]}
							{@const n = tabCounts[key]}
							<Tooltip.Root>
								<Tooltip.Trigger>
									{#snippet child({ props })}
										<Tabs.Trigger
											{...props}
											value={key}
											class="flex-none gap-1.5 rounded-none border-0 border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted-foreground shadow-none hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none dark:data-[state=active]:border-primary dark:data-[state=active]:bg-transparent"
										>
											<t.icon class="size-3.5" />
											{t.label}
											{#if n != null}
												<span
													class="text-xs tabular-nums {n === 0
														? 'text-muted-foreground/50'
														: 'text-muted-foreground'}"
												>
													{n.toLocaleString()}
												</span>
											{/if}
										</Tabs.Trigger>
									{/snippet}
								</Tooltip.Trigger>
								<Tooltip.Content side="bottom" class="flex items-center gap-1.5">
									{t.label}
									<Kbd>{i + 1}</Kbd>
								</Tooltip.Content>
							</Tooltip.Root>
						{/each}
					</Tabs.List>
				</div>
			</div>

			<Tabs.Content value="overview" class="mt-4">
				<div class="grid gap-x-8 gap-y-6 lg:grid-cols-[minmax(0,1fr)_18.5rem]">
					<div class="flex min-w-0 flex-col">
						<SurfaceStrip {summary} loading={summaryLoading} {history} onScan={handleScan} />
						<AttentionPanel
							{summary}
							checks={intel.checks}
							loading={detailLoading || summaryLoading}
							onTab={setTab}
						/>
						<HostingSection flow={hostingFlow} onPick={pickHosting} />
						<ActivityTimeline
							{target}
							{creator}
							{summary}
							{history}
							loaded={historyLoaded}
							{run}
							{now}
						/>
						<RelatedPanel groups={correlations} related={relatedDomains} loading={relatedLoading} />
					</div>
					<div
						class="border-t pt-5 lg:sticky lg:self-start lg:border-t-0 lg:border-l lg:pt-0 lg:pl-6"
						style="top: calc(var(--target-tabs-h, 0px) + 1rem)"
					>
						<Rail
							groups={intel.rail}
							{summary}
							loading={detailLoading || summaryLoading}
							{enrichedAt}
							{run}
							{now}
							{geography}
							{geoTotal}
							{geoReady}
							{live}
							onPickCountry={pickCountry}
							onTab={setTab}
							onRefresh={handleRefreshEnrichment}
						/>
					</div>
				</div>
			</Tabs.Content>

			<Tabs.Content value="web-assets" class="mt-4">
				<TargetWebAssets targetId={target.id} onScan={handleScan} />
			</Tabs.Content>

			{#if showDns}
				<Tabs.Content value="dns" class="mt-4">
					<DnsTab
						host={detail?.dns?.host ?? target.target_value}
						lookup={detail?.dns ?? null}
						status={dnsStatus}
						error={detail?.dns_error ?? target.dns_error}
						loading={detailLoading}
						refreshing={!!refreshing.dns}
						{ipsScanId}
						onRefresh={() => refreshOne('dns')}
					/>
				</Tabs.Content>
			{/if}

			<Tabs.Content value="whois" class="mt-4">
				<WhoisTab
					targetValue={target.target_value}
					targetType={target.target_type}
					record={detail?.whois ?? null}
					status={whoisStatus}
					error={detail?.whois_error ?? target.whois_error}
					loading={detailLoading}
					refreshing={!!refreshing.whois}
					onRefresh={() => refreshOne('whois')}
				/>
			</Tabs.Content>

			{#if showBgp}
				<Tabs.Content value="bgp" class="mt-4">
					<BgpTab
						targetValue={target.target_value}
						targetType={target.target_type}
						bgp={detail?.bgp ?? null}
						status={bgpStatus}
						loading={detailLoading}
						refreshing={!!refreshing.bgp}
						onRefresh={() => refreshOne('bgp')}
					/>
				</Tabs.Content>
			{/if}
		</Tabs.Root>
	{/if}
</div>

{#if target}
	<LaunchDialog
		bind:open={showLaunchModal}
		targetId={target.id}
		onClose={() => {
			showLaunchModal = false;
			refreshAll();
			scansStore.refresh();
		}}
	/>

	<ConfirmDialog
		bind:open={cancelOpen}
		title="Cancel this scan?"
		description="Stages that already finished keep their results. The scan is marked cancelled."
		confirmLabel="Cancel scan"
		loading={cancelling}
		onOpenChange={(open) => (cancelOpen = open)}
		onConfirm={confirmCancel}
	/>

	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete this target?"
		description="This also deletes every scan and finding for {target.target_value}. This action cannot be undone."
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={confirmDelete}
	/>
{/if}
