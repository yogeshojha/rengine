<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { targetsStore } from '$lib/stores/targets.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { sseStore } from '$lib/stores/sse.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { SSEChannel, SSEEventType } from '$lib/types/sse';
	import type { ActivityLog } from '$lib/types/activity';
	import { targetsApi } from '$lib/api/targets';
	import type { Target } from '$lib/types/target';
	import * as Card from '$lib/components/ui/card';
	import * as Pagination from '$lib/components/ui/pagination';
	import * as Empty from '$lib/components/ui/empty';
	import * as AlertDialog from '$lib/components/ui/alert-dialog';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import Upload from '@lucide/svelte/icons/upload';
	import Play from '@lucide/svelte/icons/play';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import X from '@lucide/svelte/icons/x';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import { toast } from 'svelte-sonner';

	import TargetFilters from '$lib/components/targets/target-filters.svelte';
	import ProjectEstateTray from '$lib/components/targets/project-estate-tray.svelte';
	import TargetViewControls from '$lib/components/targets/target-view-controls.svelte';
	import TargetsSkeleton from '$lib/components/targets/list/targets-skeleton.svelte';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import Hint from '$lib/components/hint.svelte';
	import CompareSheet from '$lib/components/scans/history/compare-sheet.svelte';
	import TargetsStrip from '$lib/components/targets/list/targets-strip.svelte';
	import TargetRow from '$lib/components/targets/list/target-row.svelte';
	import { TargetRuns } from '$lib/components/targets/list/target-runs.svelte';
	import { TCOL } from '$lib/components/targets/list/columns';
	import {
		TARGET_COLUMNS,
		TARGET_COLUMN_LABELS,
		targetPrefs
	} from '$lib/components/targets/list/prefs.svelte';
	import { TARGET_TYPE_ICONS_COMPACT } from '$lib/config/icons';
	import { TargetType, formatTargetTypePlural } from '$lib/types/target';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import * as Dialog from '$lib/components/ui/dialog';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Kbd } from '$lib/components/ui/kbd';
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import Columns3 from '@lucide/svelte/icons/columns-3';
	import Keyboard from '@lucide/svelte/icons/keyboard';
	import { forgetFindings } from '$lib/components/scans/history/findings';
	import TargetEmptyState from '$lib/components/targets/target-empty-state.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import AddTargetModal from '$lib/components/modals/add-target-modal.svelte';
	import PageSizeSelector from '$lib/components/targets/page-size-selector.svelte';
	import ScanHistoryModal from '$lib/components/targets/scan-history-modal.svelte';
	import BulkActionBar from '$lib/components/targets/bulk-action-bar.svelte';
	import ImportTargetsModal from '$lib/components/modals/import-targets-modal.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import WhoisDetailDialog from '$lib/components/whois/whois-detail-dialog.svelte';
	import BgpDetailDialog from '$lib/components/bgp-ripestat-modal/bgp-detail-dialog.svelte';
	import DnsDetailDialog from '$lib/components/dns-modal/dns-detail-dialog.svelte';
	import { downloadTargets, type ExportFormat } from '$lib/utilities/target-export';
	import type { SignalFilter, SortDir, SortKey } from '$lib/utilities/target-signals';
	import { TaskStatus } from '$lib/types/task-status';
	import { browser } from '$app/environment';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import TargetViewsMenu from '$lib/components/targets/target-views-menu.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';

	type EnrichmentKind = 'whois' | 'dns' | 'bgp';

	let urlReady = $state(false);

	function parseQuery(params: URLSearchParams) {
		const n = (v: string | null) => {
			const parsed = parseInt(v ?? '', 10);
			return Number.isFinite(parsed) ? parsed : undefined;
		};
		return {
			search: params.get('q') ?? undefined,
			activeTab: params.get('type') ?? undefined,
			signalFilter: (params.get('signal') as SignalFilter) || null,
			sortKey: (params.get('sort') as SortKey) || undefined,
			sortDir: (params.get('dir') as SortDir) || undefined,
			selectedOrganizations: params.getAll('org'),
			selectedTags: params.getAll('tag'),
			page: n(params.get('page')),
			pageSize: n(params.get('size'))
		};
	}

	function handleApplyView(query: string) {
		targetsStore.applyQueryState(parseQuery(new URLSearchParams(query)));
		targetsStore.reload();
	}

	let showAddModal = $state(false);
	let prefillValue = $state('');
	$effect(() => {
		if (!showAddModal) prefillValue = '';
	});
	let showDeleteDialog = $state(false);
	let targetToDelete = $state<Target | null>(null);
	let isDeleting = $state(false);
	let isRefreshing = $state(false);
	let showImportModal = $state(false);

	let showWhoisDialog = $state(false);
	let whoisTarget = $state<Target | null>(null);
	let whoisInitialTab = $state('overview');

	let showBgpDialog = $state(false);
	let showDnsDialog = $state(false);
	let dnsDialogTarget = $state<Target | null>(null);
	let bgpDialogTarget = $state<Target | null>(null);

	const selectedTargetIds = new SvelteSet<string>();

	function setSelection(ids: Iterable<string> = []) {
		selectedTargetIds.clear();
		for (const id of ids) selectedTargetIds.add(id);
	}

	let deleteMode = $state<'single' | 'bulk'>('single');

	let showScanHistoryModal = $state(false);
	let scanHistoryTarget = $state<Target | null>(null);

	let showLaunchModal = $state(false);
	let launchTargetId = $state<string | undefined>(undefined);
	let launchTargetIds = $state<string[] | undefined>(undefined);

	let showScheduleModal = $state(false);
	let scheduleTargetId = $state<string | undefined>(undefined);

	let showEnrichConfirm = $state(false);
	let enrichConfirmKind = $state<EnrichmentKind>('whois');

	$effect(() => {
		const activeProject = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (activeProject && hasFetched) {
			untrack(() => {
				if (!urlReady) {
					targetsStore.applyQueryState(parseQuery(page.url.searchParams));
					urlReady = true;
				}
				targetsStore.fetchAll(activeProject.slug);
			});
		}
	});

	$effect(() => {
		const qs = targetsStore.toQueryString();
		if (!urlReady || !browser) return;
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

	$effect(() => {
		const activeProject = projectsStore.activeProject;
		if (!activeProject) return;

		const unsub = sseStore.on<ActivityLog>(
			SSEChannel.project(activeProject.id),
			SSEEventType.ACTIVITY,
			async (event) => {
				if (!event.target_id) return;
				const type = event.event_type ?? '';

				if (!type.includes('.completed')) return;

				try {
					const fresh = await targetsApi.get(event.target_id);
					targetsStore.optimisticUpdateTarget(event.target_id, fresh);
				} catch {
					// ignore
				}
			}
		);

		return unsub;
	});

	let selectAllChecked = $derived<boolean | 'indeterminate'>(
		selectedTargetIds.size === 0
			? false
			: selectedTargetIds.size >= targetsStore.filteredTargets.length
				? true
				: 'indeterminate'
	);

	let deleteDialogTitle = $derived(
		deleteMode === 'single'
			? 'Delete target'
			: `Delete ${selectedTargetIds.size} target${selectedTargetIds.size !== 1 ? 's' : ''}`
	);

	let selectedTargetValues = $derived(
		targetsStore.filteredTargets
			.filter((t) => selectedTargetIds.has(t.id))
			.map((t) => t.target_value)
	);

	const BULK_PREVIEW_LIMIT = 8;

	let deletePreviewValues = $derived(selectedTargetValues.slice(0, BULK_PREVIEW_LIMIT));
	let deletePreviewRemainder = $derived(
		Math.max(0, selectedTargetIds.size - deletePreviewValues.length)
	);

	let bulkDeletePreview = $derived(
		deletePreviewValues.length
			? ` Including ${deletePreviewValues.join(', ')}${deletePreviewRemainder > 0 ? ` and ${deletePreviewRemainder} more` : ''}.`
			: ''
	);

	let deleteDialogDescription = $derived(
		deleteMode === 'single'
			? `Target ${targetToDelete?.target_value ?? ''} and its scans and findings are removed.`
			: `${selectedTargetIds.size} target${selectedTargetIds.size !== 1 ? 's' : ''} and their scans and findings are removed.${bulkDeletePreview}`
	);

	let organizationSummaries = $derived(
		targetsStore.organizations.map((org) => ({
			id: org.id,
			name: org.name,
			slug: org.slug
		}))
	);

	let tagSummaries = $derived(
		targetsStore.tags.map((tag) => ({
			id: tag.id,
			name: tag.name,
			slug: tag.slug,
			color: tag.color
		}))
	);

	let showPagination = $derived(
		targetsStore.pagination.pageSize !== -1 && targetsStore.pagination.totalPages > 1
	);

	const SIGNAL_LABELS: Record<SignalFilter, string> = {
		expiring: 'Expiring',
		attention: 'Needs attention',
		awaiting: 'Enriching',
		enriched: 'Enriched',
		monitored: 'New checks',
		unscanned: 'Not scanned',
		stale: 'Stale · 30 days',
		critical: 'Critical findings',
		high: 'High findings',
		medium: 'Medium findings'
	};

	const TYPE_TABS = [
		{ key: 'all', label: 'All' },
		...Object.keys(TARGET_TYPE_ICONS_COMPACT).map((key) => ({
			key,
			label: formatTargetTypePlural(key as TargetType)
		}))
	];

	const runs = new TargetRuns();
	const expanded = new SvelteSet<string>();
	let now = $state(Date.now());
	let focusId = $state<string | null>(null);
	let compare = $state<{ current: string; baseline: string | null } | null>(null);
	let shortcutsOpen = $state(false);
	let projectId = $derived(projectsStore.activeProject?.id ?? '');
	let rows = $derived(targetsStore.filteredTargets);
	let rowIds = $derived(rows.map((t) => t.id).join(','));
	let liveCount = $derived(rows.filter((t) => liveScans.isTargetLive(t.id)).length);

	$effect(() => {
		const t = setInterval(() => (now = Date.now()), 1000);
		return () => clearInterval(t);
	});

	$effect(() => {
		const ids = rowIds;
		const pid = projectId;
		void liveScans.completedTick;
		if (!pid || targetsStore.isLoading) return;
		untrack(() => runs.load(pid, ids ? ids.split(',') : []));
	});

	$effect(() => {
		const ids = new Set(rows.map((t) => t.id));
		for (const id of expanded) if (!ids.has(id)) expanded.delete(id);
	});

	function toggleExpand(id: string) {
		if (expanded.has(id)) expanded.delete(id);
		else expanded.add(id);
	}

	function refreshRuns() {
		for (const r of runs.runs.values()) forgetFindings(r.id);
		void runs.load(
			projectId,
			rows.map((t) => t.id)
		);
	}

	function typing(e: KeyboardEvent): boolean {
		const el = e.target as HTMLElement | null;
		return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
	}

	function onKey(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		if (e.key === '/' && !typing(e)) {
			e.preventDefault();
			document.getElementById('target-search')?.focus();
			return;
		}
		if (typing(e) || document.querySelector('[role=dialog],[role=menu]')) return;
		const idx = rows.findIndex((t) => t.id === focusId);
		const focused = idx >= 0 ? rows[idx] : null;
		const move = (d: number) => {
			const next = rows[Math.max(0, Math.min(rows.length - 1, (idx < 0 ? -1 : idx) + d))];
			if (!next) return;
			focusId = next.id;
			document.getElementById(`target-row-${next.id}`)?.scrollIntoView({ block: 'nearest' });
		};
		switch (e.key) {
			case 'j':
			case 'ArrowDown':
				e.preventDefault();
				move(1);
				break;
			case 'k':
			case 'ArrowUp':
				e.preventDefault();
				move(-1);
				break;
			case 'o':
				if (focused) toggleExpand(focused.id);
				break;
			case 'x':
				if (focused) handleTargetSelect(focused.id);
				break;
			case 's':
				if (focused) handleScan(focused);
				break;
			case 'Enter':
				if (focused) goto(ROUTES.target(focused.id));
				break;
			case '?':
				shortcutsOpen = true;
				break;
			case 'Escape':
				if (focused && expanded.has(focused.id)) expanded.delete(focused.id);
				else if (selectedTargetIds.size) clearSelection();
				break;
		}
	}

	const SHORTCUTS: [string, string][] = [
		['j / k', 'Move between targets'],
		['o', 'Expand or collapse the row'],
		['Enter', 'Open target'],
		['s', 'Scan'],
		['x', 'Select target'],
		['/', 'Search'],
		['Esc', 'Collapse or clear selection']
	];

	let activeChips = $derived.by(() => {
		const chips: { key: string; label: string; color?: string; remove: () => void }[] = [];
		const f = targetsStore.filters;
		if (f.searchQuery.trim()) {
			chips.push({
				key: 'q',
				label: `"${f.searchQuery.trim()}"`,
				remove: () => targetsStore.setSearchQuery('')
			});
		}
		for (const id of f.selectedOrganizations) {
			const org = organizationSummaries.find((o) => o.id === id);
			chips.push({
				key: `org-${id}`,
				label: org?.name ?? 'Org',
				remove: () => targetsStore.toggleOrganization(id)
			});
		}
		for (const id of f.selectedTags) {
			const tag = tagSummaries.find((t) => t.id === id);
			chips.push({
				key: `tag-${id}`,
				label: tag?.name ?? 'Tag',
				color: tag?.color,
				remove: () => targetsStore.toggleTag(id)
			});
		}
		if (f.signalFilter) {
			chips.push({
				key: 'signal',
				label: SIGNAL_LABELS[f.signalFilter],
				remove: () => targetsStore.setSignalFilter(null)
			});
		}
		return chips;
	});
	function openLaunch(targetId?: string) {
		launchTargetId = targetId;
		launchTargetIds = undefined;
		showLaunchModal = true;
	}

	function openLaunchMany(ids: string[]) {
		launchTargetId = undefined;
		launchTargetIds = ids;
		showLaunchModal = true;
	}

	function handleScan(target: Target) {
		openLaunch(target.id);
	}

	function handleSchedule(target: Target) {
		scheduleTargetId = target.id;
		showScheduleModal = true;
	}

	function handleScanAll() {
		openLaunchMany(targetsStore.filteredTargets.map((t) => t.id));
	}

	function handleTargetSelect(targetId: string) {
		if (selectedTargetIds.has(targetId)) selectedTargetIds.delete(targetId);
		else selectedTargetIds.add(targetId);
	}

	function handleSelectAll() {
		setSelection(
			selectedTargetIds.size >= targetsStore.filteredTargets.length
				? []
				: targetsStore.filteredTargets.map((t) => t.id)
		);
	}

	function clearSelection() {
		setSelection();
	}

	function handleBulkScan() {
		openLaunchMany(Array.from(selectedTargetIds));
	}

	function handleBulkDelete() {
		deleteMode = 'bulk';
		showDeleteDialog = true;
	}

	const BULK_ENRICH_CONFIRM_THRESHOLD = 25;

	async function runBulkEnrich(kind: EnrichmentKind) {
		const ids = Array.from(selectedTargetIds);
		if (ids.length === 0) return;
		try {
			const n = await targetsStore.bulkEnrich(ids, kind);
			toast.success(`${kind.toUpperCase()} queued for ${n} target${n !== 1 ? 's' : ''}`);
		} catch {
			toast.error(`${kind.toUpperCase()} not queued`);
		}
	}

	function handleBulkEnrich(kind: EnrichmentKind) {
		if (selectedTargetIds.size === 0) return;
		if (selectedTargetIds.size >= BULK_ENRICH_CONFIRM_THRESHOLD) {
			enrichConfirmKind = kind;
			showEnrichConfirm = true;
			return;
		}
		runBulkEnrich(kind);
	}

	async function handleBulkAddTag(name: string) {
		const ids = Array.from(selectedTargetIds);
		if (ids.length === 0) return;
		try {
			const n = await targetsStore.bulkAddTags(ids, [name]);
			toast.success(`Tag "${name}" added to ${n} target${n !== 1 ? 's' : ''}`);
		} catch {
			toast.error('Tag not added');
		}
	}

	async function handleBulkAddOrg(name: string) {
		const ids = Array.from(selectedTargetIds);
		if (ids.length === 0) return;
		try {
			const n = await targetsStore.bulkAddOrganizations(ids, [name]);
			toast.success(`${n} target${n !== 1 ? 's' : ''} added to "${name}"`);
		} catch {
			toast.error('Organization not added');
		}
	}

	async function handleSelectAllMatching() {
		const ids = await targetsStore.getMatchingIds();
		setSelection(ids);
		toast.success(`${ids.length} target${ids.length !== 1 ? 's' : ''} selected`);
	}

	function handleOpenScanHistory(target: Target) {
		scanHistoryTarget = target;
		showScanHistoryModal = true;
	}

	function handleDeleteTarget(target: Target) {
		targetToDelete = target;
		deleteMode = 'single';
		showDeleteDialog = true;
	}

	function handleWhoisClick(target: Target) {
		whoisTarget = target;
		whoisInitialTab = 'overview';
		showWhoisDialog = true;
	}

	function handleDiscoveriesClick(target: Target) {
		whoisTarget = target;
		whoisInitialTab = 'discoveries';
		showWhoisDialog = true;
	}

	function handleInfraClick(target: Target) {
		whoisTarget = target;
		whoisInitialTab = 'related';
		showWhoisDialog = true;
	}

	async function handleRename(target: Target, name: string) {
		const updated = await targetsStore.updateTarget(target.id, { display_name: name });
		if (updated) toast.success('Target renamed');
		else toast.error('Target not renamed');
	}

	async function handleReEnrich(target: Target, kind: EnrichmentKind) {
		try {
			if (kind === 'whois') await targetsApi.refreshWhois(target.id);
			else if (kind === 'dns') await targetsApi.refreshDns(target.id);
			else await targetsApi.refreshBgp(target.id);

			const patch: Partial<Target> =
				kind === 'whois'
					? { whois_status: TaskStatus.PENDING }
					: kind === 'dns'
						? { dns_status: TaskStatus.PENDING }
						: { bgp_status: TaskStatus.PENDING };
			targetsStore.optimisticUpdateTarget(target.id, patch);
			toast.success(`${kind.toUpperCase()} refresh started`);
		} catch {
			toast.error(`${kind.toUpperCase()} not queued`);
		}
	}

	function handleBgpClick(target: Target) {
		bgpDialogTarget = target;
		showBgpDialog = true;
	}

	function handleDnsClick(target: Target) {
		dnsDialogTarget = target;
		showDnsDialog = true;
	}

	function handleAddAsTarget(value: string) {
		prefillValue = value;
		showAddModal = true;
	}

	async function confirmDelete() {
		if (deleteMode === 'single' && !targetToDelete) return;
		isDeleting = true;

		if (deleteMode === 'single') {
			const success = await targetsStore.deleteTarget(targetToDelete!.id);
			isDeleting = false;

			if (success) {
				toast.success('Target deleted');
				showDeleteDialog = false;
				targetToDelete = null;
			} else {
				toast.error('Target not deleted');
			}
		} else {
			const ids = Array.from(selectedTargetIds);
			const ok = await targetsStore.deleteTargets(ids);
			isDeleting = false;

			const fail = ids.length - ok;
			if (ok) toast.success(`${ok} target${ok !== 1 ? 's' : ''} deleted`);
			if (fail) toast.error(`${fail} target${fail !== 1 ? 's' : ''} not deleted`);

			showDeleteDialog = false;
			setSelection();
		}
	}

	async function handleRefresh() {
		isRefreshing = true;
		await targetsStore.refresh();
		isRefreshing = false;
		if (targetsStore.error) toast.error(`Targets not refreshed. ${targetsStore.error}`);
		else toast.success('Targets refreshed');
	}

	async function handleTabChange(tab: string) {
		await targetsStore.setActiveTab(tab);
		setSelection();
	}

	function handleSearchChange(query: string) {
		targetsStore.setSearchQuery(query);
	}

	function handleOrganizationToggle(orgId: string) {
		targetsStore.toggleOrganization(orgId);
	}

	function handleTagToggle(tagId: string) {
		targetsStore.toggleTag(tagId);
	}

	function handleClearFilters() {
		targetsStore.clearFilters();
	}

	function handleSignalSelect(signal: SignalFilter | null) {
		targetsStore.setSignalFilter(signal);
	}

	function handleSort(key: SortKey) {
		targetsStore.setSort(key);
	}

	function handleExport(format: ExportFormat) {
		const rows = targetsStore.filteredTargets;
		if (rows.length === 0) {
			toast.error('No targets to export');
			return;
		}
		downloadTargets(rows, format);
		toast.success(
			`${rows.length} target${rows.length !== 1 ? 's' : ''} exported as ${format.toUpperCase()}`
		);
	}

	async function handlePageChange(page: number) {
		await targetsStore.setPage(page);
		setSelection();
	}

	async function handlePageSizeChange(size: number) {
		await targetsStore.setPageSize(size);
		setSelection();
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.targets)}</title></svelte:head>

<svelte:window onkeydown={onKey} />

{#snippet sortHead(label: string, key: SortKey, cls: string)}
	<button
		type="button"
		class="{cls} items-center gap-1 text-left tracking-wide uppercase hover:text-foreground {targetsStore
			.filters.sortKey === key
			? 'text-foreground'
			: ''}"
		onclick={() => handleSort(key)}
	>
		{label}
		{#if targetsStore.filters.sortKey === key}
			{#if targetsStore.filters.sortDir === 'desc'}<ArrowDown class="size-3" />{:else}<ArrowUp
					class="size-3"
				/>{/if}
		{/if}
	</button>
{/snippet}

<div class="flex flex-col gap-4">
	<h1 class="sr-only">Targets</h1>

	{#if projectsStore.activeProject}
		<ProjectEstateTray
			projectId={projectsStore.activeProject.id}
			onAdded={() => targetsStore.refresh()}
		/>
	{/if}

	<Card.Root class="gap-0 overflow-hidden py-0">
		<TargetsStrip
			loading={!targetsStore.hasFetched}
			summary={targetsStore.signalSummary}
			live={liveCount}
			active={targetsStore.filters.signalFilter}
			onSignal={handleSignalSelect}
		/>

		<div class="flex flex-wrap items-center justify-between gap-2 border-b px-2">
			<CountTabs
				tabs={TYPE_TABS}
				value={targetsStore.filters.activeTab}
				counts={targetsStore.counts as unknown as Record<string, number>}
				onChange={handleTabChange}
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
			<div class="min-w-[240px] flex-1">
				<TargetFilters
					searchQuery={targetsStore.filters.searchQuery}
					onSearchChange={handleSearchChange}
					organizations={organizationSummaries}
					selectedOrganizations={targetsStore.filters.selectedOrganizations}
					onOrganizationToggle={handleOrganizationToggle}
					tags={tagSummaries}
					selectedTags={targetsStore.filters.selectedTags}
					onTagToggle={handleTagToggle}
				/>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<TargetViewsMenu currentQuery={targetsStore.toQueryString()} onApply={handleApplyView} />
				<TargetViewControls
					sortKey={targetsStore.filters.sortKey}
					sortDir={targetsStore.filters.sortDir}
					onSort={handleSort}
					onExport={handleExport}
					exportDisabled={rows.length === 0}
				/>
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="outline"
								size="icon"
								class="size-9"
								aria-label="Columns and density"
							>
								<Columns3 class="size-4" />
							</Button>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content align="end" class="w-48">
						<DropdownMenu.Label>Columns</DropdownMenu.Label>
						{#each TARGET_COLUMNS as c (c)}
							<DropdownMenu.CheckboxItem
								checked={targetPrefs.shows(c)}
								onCheckedChange={() => targetPrefs.toggle(c)}
							>
								{TARGET_COLUMN_LABELS[c]}
							</DropdownMenu.CheckboxItem>
						{/each}
						<DropdownMenu.Separator />
						<DropdownMenu.Label>Density</DropdownMenu.Label>
						<DropdownMenu.RadioGroup
							value={targetPrefs.density}
							onValueChange={(v) =>
								(targetPrefs.density = v === 'compact' ? 'compact' : 'comfortable')}
						>
							<DropdownMenu.RadioItem value="comfortable">Comfortable</DropdownMenu.RadioItem>
							<DropdownMenu.RadioItem value="compact">Compact</DropdownMenu.RadioItem>
						</DropdownMenu.RadioGroup>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
				<Hint text="Refresh">
					{#snippet child(props)}
						<Button
							{...props}
							variant="outline"
							size="icon"
							class="size-9"
							aria-label="Refresh"
							onclick={handleRefresh}
							disabled={isRefreshing}
						>
							<RefreshCw class="size-4 {isRefreshing ? 'animate-spin' : ''}" />
						</Button>
					{/snippet}
				</Hint>
				<Hint text="Keyboard shortcuts">
					{#snippet child(props)}
						<Button
							{...props}
							variant="outline"
							size="icon"
							class="hidden size-9 sm:inline-flex"
							aria-label="Keyboard shortcuts"
							onclick={() => (shortcutsOpen = true)}
						>
							<Keyboard class="size-4" />
						</Button>
					{/snippet}
				</Hint>
				{#if !targetsStore.isLoading && rows.length > 0}
					<Button variant="outline" class="h-9 gap-2" onclick={handleScanAll}>
						<Play class="size-4" /> Scan {rows.length}
					</Button>
				{/if}
				<Button variant="outline" class="h-9 gap-2" onclick={() => (showImportModal = true)}>
					<Upload class="size-4" /> Import
				</Button>
				<Button class="h-9 gap-2" onclick={() => (showAddModal = true)}>
					<Plus class="size-4" /> Add target
				</Button>
			</div>
		</div>

		{#if activeChips.length > 0}
			<div class="flex flex-wrap items-center gap-1.5 border-b bg-muted/10 px-4 py-2">
				{#each activeChips as chip (chip.key)}
					<Badge variant="outline" class="gap-1 bg-background font-normal">
						{#if chip.color}
							<span class="size-2 rounded-full" style="background-color: {chip.color}"></span>
						{/if}
						{chip.label}
						<Tooltip.Root>
							<Tooltip.Trigger
								class="rounded-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
								onclick={chip.remove}
								aria-label="Remove filter {chip.label}"
							>
								<X class="size-3" />
							</Tooltip.Trigger>
							<Tooltip.Content>Remove filter {chip.label}</Tooltip.Content>
						</Tooltip.Root>
					</Badge>
				{/each}
				<button
					type="button"
					class="ml-auto text-xs text-muted-foreground hover:text-foreground"
					onclick={handleClearFilters}
				>
					Clear all
				</button>
			</div>
		{/if}

		{#if targetsStore.isLoading || !targetsStore.hasFetched}
			<TargetsSkeleton />
		{:else if targetsStore.error && rows.length === 0}
			<Empty.Root class="py-16">
				<Empty.Header>
					<Empty.Media class="size-12 rounded-2xl bg-destructive/10">
						<TriangleAlert class="size-6 text-destructive" />
					</Empty.Media>
					<Empty.Title>Targets not loaded</Empty.Title>
					<Empty.Description class="max-w-md">{targetsStore.error}</Empty.Description>
				</Empty.Header>
				<Empty.Content>
					<Button variant="outline" class="gap-2" onclick={() => targetsStore.reload()}>
						<RefreshCw class="size-4" /> Retry
					</Button>
				</Empty.Content>
			</Empty.Root>
		{:else if rows.length === 0}
			<TargetEmptyState
				hasFilters={targetsStore.hasActiveFilters}
				onAddTarget={() => (showAddModal = true)}
				onClearFilters={handleClearFilters}
			/>
		{:else}
			<div class="@container/targets w-full" role="table" aria-label="Targets">
				<div
					class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
					role="row"
				>
					<div class={TCOL.select}>
						<Checkbox
							checked={selectAllChecked === true}
							indeterminate={selectAllChecked === 'indeterminate'}
							onCheckedChange={handleSelectAll}
							aria-label="Select all targets on this page"
						/>
					</div>
					{@render sortHead('Target', 'name', `${TCOL.target} flex`)}
					{#if targetPrefs.shows('run')}<div class={TCOL.run}>Last run</div>{/if}
					{#if targetPrefs.shows('findings')}<div class={TCOL.findings}>Findings</div>{/if}
					{#if targetPrefs.shows('assets')}<div class={TCOL.assets}>Assets</div>{/if}
					{#if targetPrefs.shows('change')}<div class={TCOL.change}>Change</div>{/if}
					{#if targetPrefs.shows('organizations')}<div class={TCOL.organizations}>
							Organizations
						</div>{/if}
					{#if targetPrefs.shows('tags')}<div class={TCOL.tags}>Tags</div>{/if}
					<div class={TCOL.actions}></div>
				</div>
				{#each rows as target, i (target.id)}
					<TargetRow
						{projectId}
						{target}
						run={runs.runs.get(target.id)}
						trend={runs.trends.get(target.id)}
						loaded={runs.known.has(target.id)}
						{now}
						index={i}
						expanded={expanded.has(target.id)}
						focused={focusId === target.id}
						selected={selectedTargetIds.has(target.id)}
						scanning={liveScans.isTargetLive(target.id)}
						onToggle={() => toggleExpand(target.id)}
						onSelect={() => handleTargetSelect(target.id)}
						onFocus={() => (focusId = target.id)}
						onScan={() => handleScan(target)}
						onSchedule={() => handleSchedule(target)}
						onHistory={() => handleOpenScanHistory(target)}
						onCompare={(run) => (compare = { current: run.id, baseline: null })}
						onDelete={() => handleDeleteTarget(target)}
						onRename={(name) => handleRename(target, name)}
						onReEnrich={(kind) => handleReEnrich(target, kind)}
						onWhois={() => handleWhoisClick(target)}
						onDiscoveries={() => handleDiscoveriesClick(target)}
						onBgp={() => handleBgpClick(target)}
						onDns={() => handleDnsClick(target)}
						onInfra={() => handleInfraClick(target)}
						onChanged={refreshRuns}
					/>
				{/each}
			</div>

			<div class="flex flex-wrap items-center justify-between gap-3 border-t bg-muted/20 px-4 py-3">
				<div class="flex items-center gap-4">
					<span class="text-xs text-muted-foreground">
						{rows.length} of {targetsStore.pagination.totalItems}
						{targetsStore.pagination.totalItems === 1 ? 'target' : 'targets'}
					</span>
					{#if selectedTargetIds.size >= rows.length && selectedTargetIds.size < targetsStore.pagination.totalItems}
						<button
							type="button"
							class="text-xs font-medium text-primary hover:text-primary/80"
							onclick={handleSelectAllMatching}
						>
							Select all {targetsStore.pagination.totalItems} matching
						</button>
					{/if}
					<PageSizeSelector
						pageSize={targetsStore.pagination.pageSize}
						onPageSizeChange={handlePageSizeChange}
					/>
				</div>
				{#if showPagination}
					<Pagination.Root
						count={targetsStore.pagination.totalItems}
						perPage={targetsStore.pagination.pageSize}
						page={targetsStore.pagination.currentPage}
						onPageChange={(p) => handlePageChange(p)}
					>
						{#snippet children({ pages, currentPage })}
							<Pagination.Content>
								<Pagination.Item><Pagination.Previous /></Pagination.Item>
								{#each pages as p (p.key)}
									{#if p.type === 'ellipsis'}
										<Pagination.Item><Pagination.Ellipsis /></Pagination.Item>
									{:else}
										<Pagination.Item>
											<Pagination.Link page={p} isActive={currentPage === p.value}
												>{p.value}</Pagination.Link
											>
										</Pagination.Item>
									{/if}
								{/each}
								<Pagination.Item><Pagination.Next /></Pagination.Item>
							</Pagination.Content>
						{/snippet}
					</Pagination.Root>
				{/if}
			</div>
		{/if}
	</Card.Root>
</div>

<CompareSheet
	{projectId}
	current={compare?.current ?? null}
	baseline={compare?.baseline ?? null}
	onClose={() => (compare = null)}
/>

<Dialog.Root bind:open={shortcutsOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header><Dialog.Title>Keyboard shortcuts</Dialog.Title></Dialog.Header>
		<dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
			{#each SHORTCUTS as [k, label] (k)}
				<dt><Kbd>{k}</Kbd></dt>
				<dd class="text-muted-foreground">{label}</dd>
			{/each}
		</dl>
	</Dialog.Content>
</Dialog.Root>

<AddTargetModal bind:open={showAddModal} initialValue={prefillValue} />
<ImportTargetsModal bind:open={showImportModal} />

<LaunchDialog
	bind:open={showLaunchModal}
	targetId={launchTargetId}
	targetIds={launchTargetIds}
	onClose={() => {
		showLaunchModal = false;
		launchTargetId = undefined;
		launchTargetIds = undefined;
	}}
/>

<ScheduleModal
	bind:open={showScheduleModal}
	presetTargetIds={scheduleTargetId ? [scheduleTargetId] : undefined}
	onClose={() => {
		showScheduleModal = false;
		scheduleTargetId = undefined;
	}}
/>

<ScanHistoryModal
	bind:open={showScanHistoryModal}
	target={scanHistoryTarget}
	onOpenChange={(open) => (showScanHistoryModal = open)}
/>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title={deleteDialogTitle}
	description={deleteDialogDescription}
	{isDeleting}
	onOpenChange={(open) => (showDeleteDialog = open)}
	onConfirm={confirmDelete}
/>

<BulkActionBar
	selectedCount={selectedTargetIds.size}
	tags={tagSummaries}
	organizations={organizationSummaries}
	onScan={handleBulkScan}
	onDelete={handleBulkDelete}
	onClear={clearSelection}
	onEnrich={handleBulkEnrich}
	onAddTag={handleBulkAddTag}
	onAddOrg={handleBulkAddOrg}
/>

<WhoisDetailDialog
	bind:open={showWhoisDialog}
	recordId={whoisTarget?.whois_record_id}
	targetId={whoisTarget?.id}
	targetValue={whoisTarget?.target_value}
	targetType={whoisTarget?.target_type}
	initialTab={whoisInitialTab}
	onOpenChange={(open) => (showWhoisDialog = open)}
	onOpenTargetSummary={() => {
		goto(ROUTES.target(whoisTarget?.id ?? ''));
	}}
/>

<BgpDetailDialog
	bind:open={showBgpDialog}
	targetId={bgpDialogTarget?.id}
	targetValue={bgpDialogTarget?.target_value}
	targetType={bgpDialogTarget?.target_type}
	bgpSummary={bgpDialogTarget?.bgp}
	onOpenChange={(o) => (showBgpDialog = o)}
	onAddAsTarget={handleAddAsTarget}
/>

<DnsDetailDialog
	bind:open={showDnsDialog}
	targetId={dnsDialogTarget?.id ?? null}
	targetValue={dnsDialogTarget?.target_value ?? null}
	onOpenChange={(v) => (showDnsDialog = v)}
/>

<AlertDialog.Root bind:open={showEnrichConfirm}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>
				Re-run {enrichConfirmKind.toUpperCase()} for {selectedTargetIds.size} targets
			</AlertDialog.Title>
			<AlertDialog.Description>
				{enrichConfirmKind.toUpperCase()} lookups are queued for {selectedTargetIds.size} targets. Lookups
				are rate-limited.
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Cancel</AlertDialog.Cancel>
			<AlertDialog.Action onclick={() => runBulkEnrich(enrichConfirmKind)}>
				Queue {enrichConfirmKind.toUpperCase()}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
