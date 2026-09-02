<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore } from '$lib/stores/scans.svelte';
	import ScanActivityChart from '$lib/components/scans/scan-activity-chart.svelte';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import type { ScanRead } from '$lib/types/scan';

	let showLaunch = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);

	function newScan() {
		if (!projectsStore.activeProject) {
			toast.error('No active project selected');
			return;
		}
		launchTargetId = undefined;
		showLaunch = true;
	}

	function rescan(scan: ScanRead) {
		launchTargetId = scan.target_id;
		showLaunch = true;
	}

	function onModalClose() {
		showLaunch = false;
		launchTargetId = undefined;
		scansStore.refresh();
	}
</script>

<div class="flex flex-col gap-4">
	<h1 class="sr-only">Scans</h1>
	<ScanActivityChart stats={scansStore.stats} />
	<ScanHistoryTable onLaunch={newScan} onRescan={rescan} />
</div>

<LaunchModal bind:open={showLaunch} targetId={launchTargetId} onClose={onModalClose} />
