<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import ScanActivityChart from '$lib/components/scans/scan-activity-chart.svelte';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import type { ScanRead } from '$lib/types/scan';

	let showLaunch = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);
	let launchTargetIds = $state<string[] | undefined>(undefined);
	let rerunScan = $state<ScanRead | null>(null);

	function newScan() {
		if (!projectsStore.activeProject) {
			toast.error('No active project selected');
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

<div class="flex flex-col gap-4">
	<h1 class="sr-only">Scans</h1>
	<ScanActivityChart stats={scansStore.stats} />
	<ScanHistoryTable onLaunch={newScan} onRescan={rescan} onRescanMany={rescanMany} />
</div>

<LaunchDialog
	bind:open={showLaunch}
	targetId={launchTargetId}
	targetIds={launchTargetIds}
	rerun={rerunScan}
	onClose={onModalClose}
/>
