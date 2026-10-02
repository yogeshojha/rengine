<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { routeLabels } from '$lib/config/routes';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { untrack } from 'svelte';
	import {
		SCAN_STATUSES,
		SCAN_TIME_RANGES,
		type ScanRead,
		type ScanStatus,
		type ScanTimeRange
	} from '$lib/types/scan';

	let showLaunch = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);
	let launchTargetIds = $state<string[] | undefined>(undefined);
	let rerunScan = $state<ScanRead | null>(null);
	let targetFilters = $derived(page.url.searchParams.getAll('target'));
	let targetFilter = $derived(targetFilters.length === 1 ? targetFilters[0] : undefined);

	$effect(() => {
		const status = page.url.searchParams.get('status');
		const range = page.url.searchParams.get('range');
		const ready =
			Boolean(scansStore.filters.projectId) &&
			scansStore.filters.projectId === projectsStore.activeProject?.id;
		if (!ready) return;
		untrack(() => {
			if (status && SCAN_STATUSES.includes(status as ScanStatus))
				scansStore.setStatuses([status as ScanStatus]);
			if (range && SCAN_TIME_RANGES.some((r) => r.key === range))
				scansStore.setTimeRange(range as ScanTimeRange);
		});
	});

	function newScan() {
		if (!projectsStore.activeProject) {
			toast.error('No active project');
			return;
		}
		launchTargetId = undefined;
		launchTargetIds = undefined;
		rerunScan = null;
		showLaunch = true;
	}

	function rescan(scan: ScanRead) {
		launchTargetIds = undefined;
		launchTargetId = scan.target_id;
		rerunScan = scan;
		showLaunch = true;
	}

	function rescanMany(targetIds: string[]) {
		if (targetIds.length === 0) return;
		launchTargetId = undefined;
		launchTargetIds = targetIds;
		rerunScan = null;
		showLaunch = true;
	}

	function onModalClose() {
		showLaunch = false;
		launchTargetId = undefined;
		launchTargetIds = undefined;
		rerunScan = null;
		scansStore.refresh();
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.scans)}</title></svelte:head>

<div class="flex flex-col gap-4">
	<h1 class="sr-only">Scans</h1>
	<ScanHistoryTable
		targetId={targetFilter}
		targetIds={targetFilters}
		onLaunch={newScan}
		onRescan={rescan}
		onRescanMany={rescanMany}
	/>
</div>

<LaunchDialog
	bind:open={showLaunch}
	targetId={launchTargetId}
	targetIds={launchTargetIds}
	rerun={rerunScan}
	onClose={onModalClose}
/>
