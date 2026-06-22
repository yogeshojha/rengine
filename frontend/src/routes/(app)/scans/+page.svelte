<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { scansApi } from '$lib/api/scans';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { isLiveStatus, SCAN_POLL_MS } from '$lib/utilities/scan-status';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';
	import LaunchModal from '$lib/components/scans/launch-modal.svelte';
	import type { ScanRead, ScanStats } from '$lib/types/scan';

	let scans = $state<ScanRead[]>([]);
	let stats = $state<ScanStats | null>(null);
	let loading = $state(true);
	let refreshing = $state(false);
	let error = $state<string | null>(null);
	let showLaunch = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);
	let loadSeq = 0;

	async function load(silent = false) {
		const project = projectsStore.activeProject;
		if (!project) return;
		if (silent) refreshing = true;
		else loading = true;
		const seq = ++loadSeq;
		try {
			const rows = await scansApi.list(project.id, { limit: 500 });
			if (seq !== loadSeq) return;
			scans = rows;
			error = null;
			scansApi
				.stats(project.id)
				.then((s) => seq === loadSeq && (stats = s))
				.catch(() => {});
		} catch (e) {
			if (seq === loadSeq && !silent) error = e instanceof Error ? e.message : 'Failed to load scans';
		} finally {
			if (seq === loadSeq) {
				loading = false;
				refreshing = false;
			}
		}
	}

	let hasLive = $derived(scans.some((s) => isLiveStatus(s.status)));
	$effect(() => {
		if (!hasLive) return;
		const t = setInterval(() => load(true), SCAN_POLL_MS);
		return () => clearInterval(t);
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		if (project && projectsStore.hasFetched) untrack(() => load());
	});

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

	async function cancel(scan: ScanRead) {
		const project = projectsStore.activeProject;
		if (!project) return;
		try {
			await scansApi.cancel(scan.id, project.id);
			toast.success('Scan cancelled.');
			load(true);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to cancel scan');
		}
	}

	async function remove(scan: ScanRead) {
		const project = projectsStore.activeProject;
		if (!project) return;
		try {
			await scansApi.remove(scan.id, project.id);
			toast.success('Scan deleted.');
			load(true);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to delete scan');
		}
	}

	function onModalClose() {
		showLaunch = false;
		launchTargetId = undefined;
		load(true);
	}
</script>

<div class="space-y-5">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight">Scans</h1>
		<p class="mt-1 text-sm text-muted-foreground">
			Scan history across this project — every run of a target, with its results.
		</p>
	</div>

	<ScanHistoryTable
		{scans}
		{stats}
		{loading}
		{refreshing}
		{error}
		showSummary
		onLaunch={newScan}
		onRefresh={() => load(true)}
		onRescan={rescan}
		onCancel={cancel}
		onDelete={remove}
		onRetry={() => load()}
	/>
</div>

<LaunchModal bind:open={showLaunch} targetId={launchTargetId} onClose={onModalClose} />
