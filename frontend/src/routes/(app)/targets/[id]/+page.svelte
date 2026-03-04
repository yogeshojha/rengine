<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import { targetsApi } from '$lib/api/targets';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import { TaskStatus } from '$lib/types/task-status';
	import type { TargetDetailRead } from '$lib/types/target-detail';
	import { Button } from '$lib/components/ui/button/index.js';
	import { toast } from 'svelte-sonner';
	import { TriangleAlert, ChevronLeft } from 'lucide-svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import TargetHeader from '$lib/components/targets/target-detail/target-header.svelte';
	import TargetHeaderSkeleton from '$lib/components/targets/target-detail/target-header-skeleton.svelte';
	import OverviewStats from '$lib/components/targets/target-detail/overview/overview-stats.svelte';
	import AttackSurfaceChart from '$lib/components/targets/target-detail/overview/attack-surface-chart.svelte';
	import VulnerabilityRadar from '$lib/components/targets/target-detail/overview/vulnerability-radar.svelte';
	import RecentScans from '$lib/components/targets/target-detail/overview/recent-scans.svelte';
	import EnrichmentWidget from '$lib/components/targets/target-detail/enrichment/enrichment-widget.svelte';
	import WhoisSection from '$lib/components/targets/target-detail/enrichment/whois-section.svelte';
	import DnsSection from '$lib/components/targets/target-detail/enrichment/dns-section.svelte';
	import BgpSection from '$lib/components/targets/target-detail/enrichment/bgp-section.svelte';
	import { activityScope } from '$lib/stores/activity-scope.svelte';

	const targetId = $derived(page.params.id);

	let target = $state<Target | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state('overview');
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

	// enrichment
	let detail = $state<TargetDetailRead | null>(null);
	let detailLoading = $state(true);
	let refreshingDns = $state(false);
	let refreshingWhois = $state(false);
	let refreshingBgp = $state(false);

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

	async function fetchDetail() {
		detailLoading = true;
		try {
			detail = await targetsApi.getDetail(targetId);
		} catch {
			// widgets handle their own error states
		} finally {
			detailLoading = false;
		}
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
		if (targetId) breadcrumbStore.remove(targetId);
	});

	function handleScan() {
		if (!target) return;
		toast.success(`Scan initiated for ${target.target_value}`);
	}

	async function handleRefreshEnrichment() {
		if (!target) return;
		toast.success('Refreshing all enrichment data…');
		try {
			const promises: Promise<unknown>[] = [];
			if (showDns) promises.push(targetsApi.refreshDns(target.id));
			promises.push(targetsApi.refreshWhois(target.id));
			if (showBgp) promises.push(targetsApi.refreshBgp(target.id));
			await Promise.allSettled(promises);
			setTimeout(fetchDetail, 2000);
		} catch {
			toast.error('Some enrichments failed to refresh');
		}
	}

	async function handleRefreshDns() {
		if (!target) return;
		refreshingDns = true;
		try {
			await targetsApi.refreshDns(target.id);
			toast.success('DNS refresh initiated');
			setTimeout(fetchDetail, 2000);
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
			setTimeout(fetchDetail, 2000);
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
			setTimeout(fetchDetail, 2000);
		} catch {
			toast.error('Failed to refresh BGP');
		} finally {
			refreshingBgp = false;
		}
	}

	function handleExportJson() {
		if (!target) return;
	}
	function handleExportCsv() {
		if (!target) return;
	}

	async function confirmDelete() {
		if (!target) return;
		isDeleting = true;
		try {
			await targetsApi.delete(target.id);
			toast.success(`Target ${target.target_value} deleted`);
			showDeleteDialog = false;
			goto('/targets');
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
	<div class="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
		<div class="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
			<TriangleAlert class="h-8 w-8 text-destructive" />
		</div>
		<div class="text-center space-y-2">
			<h2 class="text-lg font-semibold">Target not found</h2>
			<p class="text-sm text-muted-foreground max-w-md">{error}</p>
		</div>
		<Button variant="outline" onclick={() => goto('/targets')}>
			<ChevronLeft class="h-4 w-4 mr-2" />
			Back to Targets
		</Button>
	</div>
{:else if target}
	<div class="space-y-6">
		<TargetHeader
			{target}
			{activeTab}
			onScan={handleScan}
			onRefreshEnrichment={handleRefreshEnrichment}
			onExportJson={handleExportJson}
			onExportCsv={handleExportCsv}
			onDelete={() => (showDeleteDialog = true)}
			onTabChange={(tab) => (activeTab = tab)}
		/>

		{#if activeTab === 'overview'}
			<div class="space-y-4">
				<!-- stats row (full width) -->
				<OverviewStats {target} />

				<!-- sidebar + main content -->
				<div class="flex flex-col lg:flex-row gap-4 items-start">
					<!-- LEFT: enrichment sidebar — each widget sizes to its own content -->
					<div class="w-full lg:w-[280px] xl:w-[300px] lg:shrink-0 space-y-3">
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
								<WhoisSection record={detail.whois} targetType={target.target_type} />
							{/if}
						</EnrichmentWidget>

						{#if showDns}
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
						{/if}

						{#if showBgp}
							<EnrichmentWidget
								title="BGP"
								status={bgpStatus}
								onRefresh={handleRefreshBgp}
								isRefreshing={refreshingBgp}
								loading={detailLoading}
							>
								{#if detail?.bgp}
									<BgpSection bgp={detail.bgp} targetType={target.target_type} />
								{/if}
							</EnrichmentWidget>
						{/if}
					</div>

					<div class="w-full lg:flex-1 min-w-0 space-y-4">
						<AttackSurfaceChart {target} />
						<VulnerabilityRadar {target} hasVulnData={true} />
						<div class="h-[450px]">
							<RecentScans {target} />
						</div>
					</div>
				</div>
			</div>
		{:else if activeTab === 'correlation'}
			<div class="text-sm text-muted-foreground text-center py-20 border border-dashed rounded-lg">
				Correlation data
			</div>
		{:else if activeTab === 'history'}
			<div class="text-sm text-muted-foreground text-center py-20 border border-dashed rounded-lg">
				Empty
			</div>
		{/if}
	</div>

	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete Target"
		description="Are you sure you want to delete '{target.target_value}'? This action cannot be undone and will remove all associated scan data."
		{isDeleting}
		onOpenChange={(open) => (showDeleteDialog = open)}
		onConfirm={confirmDelete}
	/>
{/if}
