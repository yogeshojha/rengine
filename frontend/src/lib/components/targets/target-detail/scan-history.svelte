<script lang="ts">
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';

	interface Props {
		targetId: string;
		onLaunch?: () => void;
	}
	let { targetId, onLaunch }: Props = $props();
</script>

<ScanHistoryTable {targetId} onLaunch={() => onLaunch?.()} onRescan={() => onLaunch?.()} />
