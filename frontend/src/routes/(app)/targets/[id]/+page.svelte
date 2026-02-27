<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import { targetsApi } from '$lib/api/targets';
	import { breadcrumbStore } from '$lib/stores/breadcrumbs.svelte';
	import type { Target } from '$lib/types/target';
	import { TargetType } from '$lib/types/target';
	import { Button } from '$lib/components/ui/button/index.js';
	import { toast } from 'svelte-sonner';
	import { TriangleAlert, ChevronLeft } from 'lucide-svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import TargetHeader from '$lib/components/targets/target-detail/target-header.svelte';
	import TargetHeaderSkeleton from '$lib/components/targets/target-detail/target-header-skeleton.svelte';
	import OverviewStats from '$lib/components/targets/target-detail/overview/overview-stats.svelte';
	import AttackSurfaceChart from '$lib/components/targets/target-detail/overview/attack-surface-chart.svelte';
	import VulnerabilityRadar from '$lib/components/targets/target-detail/overview/vulnerability-radar.svelte';
	import ActivityHeatmap from '$lib/components/targets/target-detail/overview/activity-heatmap.svelte';
	import RecentScans from '$lib/components/targets/target-detail/overview/recent-scans.svelte';
	import AssetGeography from '@/components/targets/target-detail/overview/asset-geography.svelte';
	import { activityScope } from '$lib/stores/activity-scope.svelte';

	const targetId = $derived(page.params.id);

	let target = $state<Target | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state('overview');
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

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

	$effect(() => {
		if (targetId) fetchTarget();
		activityScope.targetId = targetId;
		return () => activityScope.clear();
	});

	onDestroy(() => {
		if (targetId) breadcrumbStore.remove(targetId);
	});

	function handleScan() {
		if (!target) return;
		// TODO: open scan config modal
		toast.success(`Scan initiated for ${target.target_value}`);
	}

	async function handleRefreshEnrichment() {
		if (!target) return;
		toast.success('Refreshing all enrichment data…');
		try {
			const promises: Promise<unknown>[] = [];
			if ([TargetType.DOMAIN, TargetType.URL].includes(target.target_type)) {
				promises.push(targetsApi.refreshDns(target.id));
			}
			promises.push(targetsApi.refreshWhois(target.id));
			if ([TargetType.IP, TargetType.IP_RANGE, TargetType.ASN].includes(target.target_type)) {
				promises.push(targetsApi.refreshBgp(target.id));
			}
			await Promise.allSettled(promises);
			await fetchTarget();
			toast.success('Enrichment refresh complete');
		} catch {
			toast.error('Some enrichments failed to refresh');
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
				<OverviewStats {target} />

				<!-- Row 1: Attack Surface + Vulnerability Radar -->
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
					<div class="lg:col-span-2">
						<AttackSurfaceChart {target} />
					</div>
					<div class="lg:col-span-1">
						<VulnerabilityRadar {target} hasVulnData={true} />
					</div>
				</div>

				<!-- Row 2: Activity Heatmap + Geography -->
				<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
					<div class="lg:col-span-2">
						<ActivityHeatmap {target} />
					</div>
					<div class="lg:col-span-1">
						<AssetGeography {target} />
					</div>
				</div>

				<!-- Row 3: Activity Feed + Recent Scans -->
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div class="h-[450px]">
						<RecentScans {target} />
					</div>
				</div>
			</div>
		{:else if activeTab === 'enrichment'}
			<div class="text-sm text-muted-foreground text-center py-20 border border-dashed rounded-lg">
				Enrichment data
			</div>
		{:else if activeTab === 'correlation'}
			<div class="text-sm text-muted-foreground text-center py-20 border border-dashed rounded-lg">
				Corelation data
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
