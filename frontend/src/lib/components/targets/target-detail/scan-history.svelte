<script lang="ts">
	import { onDestroy, untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';
	import { scansApi } from '$lib/api/scans';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { isLiveStatus } from '$lib/utilities/scan-status';
	import type { ScanRead } from '$lib/types/scan';

	interface Props {
		targetId: string;
		onLaunch?: () => void;
	}
	let { targetId, onLaunch }: Props = $props();

	let scans = $state<ScanRead[]>([]);
	let loading = $state(true);
	let refreshing = $state(false);
	let error = $state<string | null>(null);
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	async function load(silent = false) {
		const project = projectsStore.activeProject;
		if (!project) return;
		if (silent) refreshing = true;
		else loading = true;
		try {
			scans = await scansApi.list(project.id, { target_id: targetId, limit: 500 });
			error = null;
		} catch (e) {
			if (!silent) error = e instanceof Error ? e.message : 'Failed to load scan history';
		} finally {
			loading = false;
			refreshing = false;
		}
	}

	let hasLive = $derived(scans.some((s) => isLiveStatus(s.status)));
	$effect(() => {
		if (!hasLive) return;
		const t = setInterval(() => load(true), 4000);
		return () => clearInterval(t);
	});

	$effect(() => {
		const project = projectsStore.activeProject;
		const tid = targetId;
		if (project && tid) untrack(() => load());
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
	});

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
</script>

<ScanHistoryTable
	{scans}
	{loading}
	{refreshing}
	{error}
	{targetId}
	onLaunch={() => onLaunch?.()}
	onRefresh={() => load(true)}
	onRescan={() => onLaunch?.()}
	onCancel={cancel}
	onDelete={remove}
	onRetry={() => load()}
/>
