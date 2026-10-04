<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { page } from '$app/state';
	import { browser } from '$app/environment';
	import { goto, replaceState } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { targetsApi } from '$lib/api/targets';
	import { plural } from '$lib/utilities/strings';
	import { SCAN_STATUS_TABS } from '$lib/utilities/scan-status';

	import { projectsStore } from '$lib/stores/projects.svelte';
	import { scansStore, type ScanView } from '$lib/stores/scans.svelte';
	import ScanHistoryTable from '$lib/components/scans/scan-history-table.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import { untrack } from 'svelte';
	import {
		SCAN_SORT_KEYS,
		SCAN_STATUSES,
		SCAN_TIME_RANGES,
		type ScanRead,
		type ScanSortKey,
		type ScanStatus
	} from '$lib/types/scan';

	let showLaunch = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);
	let launchTargetIds = $state<string[] | undefined>(undefined);
	let rerunScan = $state<ScanRead | null>(null);
	let targetFilters = $derived(page.url.searchParams.getAll('target'));
	let targetFilter = $derived(targetFilters.length === 1 ? targetFilters[0] : undefined);
	let targetValue = $state<string | null>(null);
	let scopeLabel = $derived(
		targetFilters.length > 1
			? plural(targetFilters.length, 'target')
			: (targetValue ??
					scansStore.scans.find((s) => s.target_id === targetFilter)?.execution_config
						.target_value ??
					'Target')
	);

	$effect(() => {
		const id = targetFilter;
		targetValue = null;
		if (!id) return;
		let live = true;
		targetsApi
			.get(id)
			.then((t) => {
				if (live) targetValue = t.target_value;
			})
			.catch(() => {});
		return () => {
			live = false;
		};
	});

	let lastProject: string | undefined;
	$effect(() => {
		const pid = projectsStore.activeProject?.id;
		untrack(() => {
			if (!pid) return;
			const stale = lastProject !== undefined && lastProject !== pid;
			lastProject = pid;
			if (stale && targetFilters.length) goto(ROUTES.scans, { replaceState: true });
		});
	});

	function parseView(params: URLSearchParams): ScanView {
		const n = (v: string | null) => {
			const parsed = parseInt(v ?? '', 10);
			return Number.isFinite(parsed) ? parsed : undefined;
		};
		const date = (key: string) => {
			const v = params.get(key);
			return v && !Number.isNaN(Date.parse(v)) ? new Date(v).toISOString() : null;
		};
		const dated = params.has('from') || params.has('to');
		const sort = params.get('sort') as ScanSortKey | null;
		const dir = params.get('dir');
		const size = n(params.get('size'));
		const pageNo = n(params.get('page'));
		return {
			query: params.get('q') ?? undefined,
			statuses: params.has('status')
				? params
						.getAll('status')
						.flatMap(
							(s) =>
								SCAN_STATUS_TABS.find((t) => t.key === s)?.statuses ??
								(SCAN_STATUSES.includes(s as ScanStatus) ? [s as ScanStatus] : [])
						)
				: undefined,
			range: dated ? undefined : SCAN_TIME_RANGES.find((r) => r.key === params.get('range'))?.key,
			startedFrom: dated ? date('from') : undefined,
			startedTo: dated ? date('to') : undefined,
			latest: params.has('view') ? params.get('view') === 'latest' : undefined,
			sortKey: sort && SCAN_SORT_KEYS.includes(sort) ? sort : undefined,
			sortDir: dir === 'asc' || dir === 'desc' ? dir : undefined,
			page: pageNo !== undefined && pageNo >= 1 ? pageNo : undefined,
			pageSize: size !== undefined && size >= 1 && size <= 100 ? size : undefined
		};
	}

	let appliedHref = $state<string | null>(null);

	$effect.pre(() => {
		const pid = projectsStore.activeProject?.id;
		const href = page.url.href;
		if (!pid || !projectsStore.hasFetched) return;
		untrack(() => {
			if (href === appliedHref) return;
			const params = browser ? new URLSearchParams(location.search) : page.url.searchParams;
			scansStore.init(pid, targetFilters, parseView(params));
			appliedHref = href;
		});
	});

	$effect(() => {
		const qs = scansStore.toQueryString();
		if (!browser || appliedHref !== page.url.href) return;
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {}
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
		{scopeLabel}
		onClearScope={() => goto(ROUTES.scans)}
	/>
</div>

<LaunchDialog
	bind:open={showLaunch}
	targetId={launchTargetId}
	targetIds={launchTargetIds}
	rerun={rerunScan}
	onClose={onModalClose}
/>
