<script lang="ts">
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { onDestroy, untrack } from 'svelte';
	import { targetsApi } from '$lib/api/targets';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as Empty from '$lib/components/ui/empty';
	import { toast } from 'svelte-sonner';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import LayoutDashboard from '@lucide/svelte/icons/layout-dashboard';
	import FileText from '@lucide/svelte/icons/file-text';
	import Network from '@lucide/svelte/icons/network';
	import Link2 from '@lucide/svelte/icons/link-2';
	import ShieldAlert from '@lucide/svelte/icons/shield-alert';
	import EthernetPort from '@lucide/svelte/icons/ethernet-port';
	import Cpu from '@lucide/svelte/icons/cpu';
	import History from '@lucide/svelte/icons/history';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import TargetHeader from '$lib/components/targets/target-detail/target-header.svelte';
	import TargetHeaderSkeleton from '$lib/components/targets/target-detail/target-header-skeleton.svelte';
	import EnrichmentWidget from '$lib/components/targets/target-detail/enrichment/enrichment-widget.svelte';
	import WhoisSection from '$lib/components/targets/target-detail/enrichment/whois-section.svelte';
	import DnsSection from '$lib/components/targets/target-detail/enrichment/dns-section.svelte';
	import BgpSection from '$lib/components/targets/target-detail/enrichment/bgp-section.svelte';
	import TargetVitals from '$lib/components/targets/target-detail/summary/target-vitals.svelte';
	import SecurityPosture from '$lib/components/targets/target-detail/summary/security-posture.svelte';
	import TargetInfra from '$lib/components/targets/target-detail/summary/target-infra.svelte';
	import TargetMeta from '$lib/components/targets/target-detail/summary/target-meta.svelte';
	import ScanTabEmpty from '$lib/components/targets/target-detail/summary/scan-tab-empty.svelte';
	import ScanHistory from '$lib/components/targets/target-detail/scan-history.svelte';
	import TargetSubdomains from '$lib/components/targets/target-detail/target-subdomains.svelte';
	import { buildTargetSummary } from '$lib/components/targets/target-detail/summary/derive';
	import { activityScope } from '$lib/stores/activity-scope.svelte';
	import { ROUTES } from '$lib/config/routes';
	import type { IconComponent } from '$lib/config/icons';

	const targetId = $derived(page.params.id ?? '');

	let target = $state<Target | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let showLaunchModal = $state(false);

	let detail = $state<TargetDetailRead | null>(null);
	let detailLoading = $state(true);
	let detailError = $state<string | null>(null);
	let refreshingDns = $state(false);
	let refreshingWhois = $state(false);
	let refreshingBgp = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	let showDns = $derived(
		target?.target_type === TargetType.DOMAIN || target?.target_type === TargetType.URL
	);
	let showBgp = $derived(
		target?.target_type === TargetType.IP ||
			target?.target_type === TargetType.IP_RANGE ||
			target?.target_type === TargetType.ASN
	);

	let whoisStatus = $derived(detail?.whois_status ?? target?.whois_status ?? TaskStatus.PENDING);
	let dnsStatus = $derived(detail?.dns_status ?? target?.dns_status ?? TaskStatus.PENDING);
	let bgpStatus = $derived(detail?.bgp_status ?? target?.bgp_status ?? TaskStatus.PENDING);

	let activeTab = $state(page.url.searchParams.get('tab') ?? 'overview');

	let hasInfra = $derived(target ? buildTargetSummary(target, detail).infra.length > 0 : false);

	let scanTabs = $derived.by(() => {
		const tabs: Array<{
			value: string;
			label: string;
			icon: IconComponent;
			title: string;
			description: string;
		}> = [];
		if (showDns) {
			tabs.push({
				value: 'subdomains',
				label: 'Subdomains',
				icon: Network,
				title: 'No subdomains discovered yet',
				description: 'Run a reconnaissance scan to enumerate subdomains for this target.'
			});
			tabs.push({
				value: 'endpoints',
				label: 'Endpoints',
				icon: Link2,
				title: 'No endpoints discovered yet',
				description: 'Run a scan to crawl and discover URLs and API endpoints.'
			});
		}
		tabs.push({
			value: 'vulnerabilities',
			label: 'Vulnerabilities',
			icon: ShieldAlert,
			title: 'No vulnerabilities found yet',
			description: 'Run a vulnerability scan to surface findings for this target.'
		});
		tabs.push({
			value: 'ports',
			label: 'Ports',
			icon: EthernetPort,
			title: 'No open ports discovered yet',
			description: 'Run a port scan to map the exposed services on this target.'
		});
		tabs.push({
			value: 'technologies',
			label: 'Technologies',
			icon: Cpu,
			title: 'No technologies detected yet',
			description: 'Run a scan to fingerprint the technology stack of this target.'
		});
		tabs.push({
			value: 'scan-history',
			label: 'Scan History',
			icon: History,
			title: 'No scans yet',
			description: 'Launch a scan to start building scan history for this target.'
		});
		return tabs;
	});

	let validTabs = $derived(new Set(['overview', 'details', ...scanTabs.map((t) => t.value)]));

	$effect(() => {
		if (target && !validTabs.has(activeTab)) activeTab = 'overview';
	});

	$effect(() => {
		const tab = activeTab;
		if (!browser) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (tab === 'overview') params.delete('tab');
		else params.set('tab', tab);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

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
		const maxAttempts = 30;
		pollTimer = setInterval(async () => {
			attempts += 1;
			await fetchDetail(true);
			if (!hasPendingEnrichment() || attempts >= maxAttempts) stopPolling();
		}, 2500);
	}

	$effect(() => {
		if (targetId) {
			fetchTarget();
			fetchDetail();
		}
		activityScope.targetId = targetId;
		return () => activityScope.clear();
	});

	onDestroy(() => {
		stopPolling();
		if (targetId) breadcrumbStore.remove(targetId);
	});

	function handleScan() {
		if (!target) return;
		showLaunchModal = true;
	}

	async function handleRefreshEnrichment() {
		if (!target) return;
		toast.info('Enrichment refresh initiated…');
		const promises: Promise<unknown>[] = [];
		if (showDns) promises.push(targetsApi.refreshDns(target.id));
		promises.push(targetsApi.refreshWhois(target.id));
		if (showBgp) promises.push(targetsApi.refreshBgp(target.id));
		const results = await Promise.allSettled(promises);
		const failed = results.filter((r) => r.status === 'rejected').length;
		if (failed > 0) {
			toast.error(
				failed === results.length
					? 'Failed to refresh enrichment'
					: `${failed} of ${results.length} enrichments failed to refresh`
			);
		}
		startPolling();
	}

	async function handleRefreshDns() {
		if (!target) return;
		refreshingDns = true;
		try {
			await targetsApi.refreshDns(target.id);
			toast.success('DNS refresh initiated');
			startPolling();
		} catch {
			toast.error('Failed to refresh DNS');
		} finally {
			refreshingDns = false;
		}
	}

	async function handleRefreshWhois() {
		if (!target) return;
		refreshingWhois = true;
		try {
			await targetsApi.refreshWhois(target.id);
			toast.success('WHOIS refresh initiated');
			startPolling();
		} catch {
			toast.error('Failed to refresh WHOIS');
		} finally {
			refreshingWhois = false;
		}
	}

	async function handleRefreshBgp() {
		if (!target) return;
		refreshingBgp = true;
		try {
			await targetsApi.refreshBgp(target.id);
			toast.success('BGP refresh initiated');
			startPolling();
		} catch {
			toast.error('Failed to refresh BGP');
		} finally {
			refreshingBgp = false;
		}
	}

	function downloadBlob(content: string, mime: string, ext: string) {
		if (!target) return;
		const blob = new Blob([content], { type: mime });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `${target.target_value.replace(/[^a-z0-9.-]+/gi, '_')}.${ext}`;
		a.click();
		URL.revokeObjectURL(url);
	}

	function handleExportJson() {
		if (!target) return;
		downloadBlob(JSON.stringify({ target, detail }, null, 2), 'application/json', 'json');
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
			['created_at', target.created_at],
			['updated_at', target.updated_at]
		];
		const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
		const csv = ['field,value', ...rows.map(([k, v]) => `${esc(k)},${esc(v)}`)].join('\n');
		downloadBlob(csv, 'text/csv', 'csv');
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

{#if isLoading}
	<TargetHeaderSkeleton />
{:else if error}
	<Empty.Root class="min-h-[50vh] border-none">
		<Empty.Header>
			<Empty.Media
				variant="icon"
				class="h-16 w-16 rounded-full bg-destructive/10 text-destructive [&_svg:not([class*='size-'])]:size-8"
			>
				<TriangleAlert />
			</Empty.Media>
			<Empty.Title>Target not found</Empty.Title>
			<Empty.Description class="max-w-md">{error}</Empty.Description>
		</Empty.Header>
		<Empty.Content>
			<Button variant="outline" onclick={() => goto(ROUTES.targets)}>
				<ChevronLeft class="h-4 w-4 mr-2" />
				Back to targets
			</Button>
		</Empty.Content>
	</Empty.Root>
{:else if target}
	<div class="space-y-5">
		<TargetHeader
			{target}
			onScan={handleScan}
			onRefreshEnrichment={handleRefreshEnrichment}
			onExportJson={handleExportJson}
			onExportCsv={handleExportCsv}
			onDelete={() => (showDeleteDialog = true)}
		/>

		{#snippet whoisWidget(t: Target)}
			<EnrichmentWidget
				title="WHOIS"
				status={whoisStatus}
				error={detail?.whois_error}
				queriedAt={detail?.whois?.queried_at}
				onRefresh={handleRefreshWhois}
				isRefreshing={refreshingWhois}
				loading={detailLoading}
			>
				{#if detail?.whois}
					<WhoisSection record={detail.whois} targetType={t.target_type} />
				{/if}
			</EnrichmentWidget>
		{/snippet}

		<Tabs.Root
			value={activeTab}
			onValueChange={(v) => {
				if (v) activeTab = v;
			}}
		>
			<Tabs.List class="h-auto w-full flex-wrap justify-start gap-1">
				<Tabs.Trigger value="overview" class="gap-1.5">
					<LayoutDashboard class="h-3.5 w-3.5" />
					Overview
				</Tabs.Trigger>
				<Tabs.Trigger value="details" class="gap-1.5">
					<FileText class="h-3.5 w-3.5" />
					Details
				</Tabs.Trigger>
				{#each scanTabs as t (t.value)}
					{@const TabIcon = t.icon}
					<Tabs.Trigger value={t.value} class="gap-1.5">
						<TabIcon class="h-3.5 w-3.5" />
						{t.label}
					</Tabs.Trigger>
				{/each}
			</Tabs.List>

			<Tabs.Content value="overview" class="mt-4 space-y-3">
				{#if detailError && !detailLoading}
					<div
						class="flex items-center justify-between gap-3 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3"
					>
						<div class="flex items-center gap-2">
							<TriangleAlert class="h-4 w-4 shrink-0 text-destructive" />
							<p class="text-xs text-destructive/90">
								Couldn't load enrichment details — {detailError}
							</p>
						</div>
						<Button variant="outline" size="sm" onclick={() => fetchDetail()}>
							<RefreshCw class="h-3.5 w-3.5 mr-1.5" />
							Retry
						</Button>
					</div>
				{/if}
				<TargetVitals {target} {detail} loading={detailLoading} />
				{#if hasInfra}
					<div class="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
						<SecurityPosture {target} {detail} loading={detailLoading} />
						<TargetInfra {target} {detail} />
					</div>
				{:else}
					<SecurityPosture {target} {detail} loading={detailLoading} />
				{/if}
			</Tabs.Content>

			<Tabs.Content value="details" class="mt-4 space-y-3">
				{#if detailError && !detailLoading}
					<div
						class="flex items-center justify-between gap-3 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3"
					>
						<div class="flex items-center gap-2">
							<TriangleAlert class="h-4 w-4 shrink-0 text-destructive" />
							<p class="text-xs text-destructive/90">
								Couldn't load enrichment details — {detailError}
							</p>
						</div>
						<Button variant="outline" size="sm" onclick={() => fetchDetail()}>
							<RefreshCw class="h-3.5 w-3.5 mr-1.5" />
							Retry
						</Button>
					</div>
				{/if}
				{#if showDns}
					<div class="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
						<EnrichmentWidget
							title="DNS"
							status={dnsStatus}
							error={detail?.dns_error}
							queriedAt={detail?.dns?.queried_at}
							onRefresh={handleRefreshDns}
							isRefreshing={refreshingDns}
							loading={detailLoading}
						>
							{#if detail?.dns}
								<DnsSection lookup={detail.dns} />
							{/if}
						</EnrichmentWidget>
						{@render whoisWidget(target)}
					</div>
				{:else}
					{@render whoisWidget(target)}
					{#if showBgp}
						<EnrichmentWidget
							title="BGP"
							status={bgpStatus}
							onRefresh={handleRefreshBgp}
							isRefreshing={refreshingBgp}
							loading={detailLoading}
						>
							{#if detail?.bgp}
								<BgpSection bgp={detail.bgp} />
							{/if}
						</EnrichmentWidget>
					{/if}
				{/if}
			</Tabs.Content>

			{#each scanTabs as t (t.value)}
				<Tabs.Content value={t.value} class="mt-4">
					{#if t.value === 'scan-history'}
						<ScanHistory targetId={target.id} onLaunch={handleScan} />
					{:else if t.value === 'subdomains'}
						<TargetSubdomains targetId={target.id} onScan={handleScan} />
					{:else}
						<ScanTabEmpty
							icon={t.icon}
							title={t.title}
							description={t.description}
							onScan={handleScan}
						/>
					{/if}
				</Tabs.Content>
			{/each}
		</Tabs.Root>

		<TargetMeta {target} />
	</div>

	<LaunchModal
		bind:open={showLaunchModal}
		targetId={target.id}
		onClose={() => (showLaunchModal = false)}
	/>

	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete this target?"
		description="This also deletes every scan and finding for {target.target_value}."
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={confirmDelete}
	/>
{/if}
