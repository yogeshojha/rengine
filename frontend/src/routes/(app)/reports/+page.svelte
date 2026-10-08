<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { page } from '$app/state';
	import { goto, replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { ScrollArea } from '$lib/components/ui/scroll-area';
	import { Button } from '$lib/components/ui/button/index.js';
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import LayoutTemplateIcon from '@lucide/svelte/icons/layout-template';
	import PaletteIcon from '@lucide/svelte/icons/palette';
	import TypeIcon from '@lucide/svelte/icons/type';
	import StampIcon from '@lucide/svelte/icons/stamp';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import SearchIcon from '@lucide/svelte/icons/search';
	import XIcon from '@lucide/svelte/icons/x';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import PageHeader from '$lib/components/page-header.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import FilterChips from '$lib/components/scans/results/table/filter-chips.svelte';
	import ReportRow from '$lib/components/reports/report-row.svelte';
	import TemplatesPanel from '$lib/components/reports/templates-panel.svelte';
	import ThemesPanel from '$lib/components/reports/themes-panel.svelte';
	import TypefacesPanel from '$lib/components/reports/typefaces-panel.svelte';
	import ThemeUploadDialog from '$lib/components/reports/theme-upload-dialog.svelte';
	import FontUploadDialog from '$lib/components/reports/font-upload-dialog.svelte';
	import DefaultsPanel from '$lib/components/reports/defaults-panel.svelte';
	import UnsavedChangesDialog from '$lib/components/unsaved-changes-dialog.svelte';
	import GenerateDialog from '$lib/components/reports/generate-dialog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { reports as reportsStore } from '$lib/stores/reports.svelte';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { REPORT_TABS, ROUTES, routeLabels, type ReportTab } from '$lib/config/routes';
	import LoadingButton from '$lib/components/loading-button.svelte';
	import LoadNotice from '$lib/components/load-notice.svelte';
	import { toast } from 'svelte-sonner';
	import type { ReportTemplate } from '$lib/types/report';

	const DEFAULT_TAB: ReportTab = 'reports';
	const valid = new Set<string>(REPORT_TABS);
	const shownParams = () =>
		browser ? new URLSearchParams(location.search) : page.url.searchParams;
	const landed = shownParams();
	const initial = landed.get('tab') ?? DEFAULT_TAB;

	let activeTab = $state<ReportTab>(valid.has(initial) ? (initial as ReportTab) : DEFAULT_TAB);
	let search = $state(landed.get('q') ?? '');
	let generateOpen = $state(false);
	let generateTemplate = $state('');
	let uploadOpen = $state(false);
	let fontUploadOpen = $state(false);
	let pendingDelete = $state<{
		kind: 'report' | 'template' | 'theme' | 'typeface';
		id: string;
		name: string;
	} | null>(null);
	let deleting = $state(false);

	const selectedIds = new SvelteSet<string>();

	const projectId = $derived(projectsStore.activeProject?.id ?? '');
	const stale = $derived(!!projectId && reportsStore.rowsProjectId !== projectId);
	const isAdmin = $derived(auth.user?.is_superuser ?? false);
	const scanFilter = $derived(page.url.searchParams.get('scan') ?? undefined);
	const targetFilter = $derived(page.url.searchParams.get('target') ?? undefined);

	const visibleReports = $derived(
		reportsStore.reports
			.filter(
				(r) =>
					(!scanFilter || r.scan_id === scanFilter) &&
					(!targetFilter || r.target_id === targetFilter)
			)
			.filter((r) => {
				const q = search.trim().toLowerCase();
				return !q || r.title.toLowerCase().includes(q) || r.subject.toLowerCase().includes(q);
			})
	);

	const filtered = $derived(visibleReports.length !== reportsStore.reports.length);

	const subjectChips = $derived.by(() => {
		const chips: { id: 'scan' | 'target'; label: string }[] = [];
		if (scanFilter) {
			const name = reportsStore.reports.find((r) => r.scan_id === scanFilter)?.subject;
			chips.push({ id: 'scan', label: name ? `Scan ${name}` : 'Selected scan' });
		}
		if (targetFilter) {
			const name = reportsStore.reports.find((r) => r.target_id === targetFilter)?.subject;
			chips.push({ id: 'target', label: name ? `Target ${name}` : 'Selected target' });
		}
		return chips;
	});

	function clearSubject(param?: 'scan' | 'target') {
		const url = new URL(location.href);
		for (const key of param ? [param] : ['scan', 'target']) url.searchParams.delete(key);
		void goto(`${url.pathname}${url.search}`, {
			replaceState: true,
			noScroll: true,
			keepFocus: true
		});
	}

	const selectedCount = $derived(selectedIds.size);
	const selectableIds = $derived(visibleReports.map((r) => r.id));
	const selectAllChecked = $derived<boolean | 'indeterminate'>(
		selectableIds.length > 0 && selectableIds.every((id) => selectedIds.has(id))
			? true
			: selectedCount > 0
				? 'indeterminate'
				: false
	);

	$effect(() => {
		const ids = new Set(reportsStore.reports.map((r) => r.id));
		for (const id of selectedIds) if (!ids.has(id)) selectedIds.delete(id);
	});

	function toggleReport(id: string) {
		if (selectedIds.has(id)) selectedIds.delete(id);
		else selectedIds.add(id);
	}

	function toggleSelectAll() {
		if (selectableIds.every((id) => selectedIds.has(id))) selectedIds.clear();
		else for (const id of selectableIds) selectedIds.add(id);
	}

	function clearSelection() {
		selectedIds.clear();
	}

	let shownProject = '';
	$effect(() => {
		const id = projectId;
		if (!id) return;
		untrack(() => {
			if (shownProject && shownProject !== id) search = '';
			shownProject = id;
			void reportsStore.fetch(id);
			void reportsStore.fetchTemplates(id);
			void reportCatalog.fetch();
		});
	});

	$effect(() => {
		void page.url.href;
		const shown = untrack(shownParams);
		const tab = shown.get('tab') ?? DEFAULT_TAB;
		const q = shown.get('q') ?? '';
		untrack(() => {
			if (valid.has(tab) && tab !== activeTab) activeTab = tab as ReportTab;
			if (q !== search.trim()) search = q;
		});
	});

	$effect(() => {
		const tab = activeTab;
		const q = search.trim();
		if (!browser) return;
		const params = untrack(shownParams);
		if (tab === DEFAULT_TAB) params.delete('tab');
		else params.set('tab', tab);
		if (q) params.set('q', q);
		else params.delete('q');
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

	let defaultsDirty = $state(false);
	let brandingResets = $state(0);
	let leaveTabOpen = $state(false);
	let pendingTab = $state<ReportTab | null>(null);

	function requestTab(tab: ReportTab) {
		if (activeTab === 'branding' && tab !== 'branding' && defaultsDirty) {
			pendingTab = tab;
			leaveTabOpen = true;
			return;
		}
		activeTab = tab;
	}

	async function duplicate(template: ReportTemplate) {
		const created = await reportsStore.createTemplate(projectId, {
			name: `${template.name} copy`,
			description: template.description,
			title: template.title,
			subtitle: template.subtitle,
			scope: template.scope,
			theme: template.theme,
			formats: template.formats,
			clone_of: template.id
		});
		if (created) {
			toast.success(`Template ${created.name} created`);
			void goto(ROUTES.reportTemplate(created.id));
		}
	}

	let creatingTemplate = $state(false);
	let catalogRetrying = $state(false);

	async function retryCatalog() {
		catalogRetrying = true;
		await reportCatalog.fetch(true);
		catalogRetrying = false;
	}

	async function newTemplate() {
		if (!projectId || creatingTemplate) return;
		creatingTemplate = true;
		const sections = (reportCatalog.catalog?.sections ?? [])
			.filter((s) => s.default_enabled)
			.map((s) => ({ section: s.name, enabled: true, title: '', config: {} }));
		const created = await reportsStore.createTemplate(projectId, {
			name: 'Untitled template',
			sections
		});
		creatingTemplate = false;
		if (created) void goto(ROUTES.reportTemplate(created.id));
	}

	const deleteDescription = $derived(
		pendingDelete?.kind === 'template'
			? `Template ${pendingDelete.name} is removed.`
			: pendingDelete?.kind === 'theme'
				? `Theme ${pendingDelete.name} is removed.`
				: pendingDelete?.kind === 'typeface'
					? `Typeface ${pendingDelete.name} and its font files are removed.`
					: `Report ${pendingDelete?.name ?? ''} and its files are removed.`
	);

	const DELETE_NOUN = {
		report: 'Report',
		template: 'Template',
		theme: 'Theme',
		typeface: 'Typeface'
	} as const;

	async function confirmDelete() {
		if (!pendingDelete) return;
		const { kind, id } = pendingDelete;
		deleting = true;
		let ok = false;
		if (kind === 'report') ok = await reportsStore.remove(projectId, id);
		else if (kind === 'template') ok = await reportsStore.removeTemplate(projectId, id);
		else {
			try {
				if (kind === 'theme') await reportsApi.deleteTheme(id);
				else await reportsApi.deleteFont(id);
				await reportCatalog.fetch(true);
				ok = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : `${DELETE_NOUN[kind]} not deleted`);
			}
		}
		deleting = false;
		if (!ok) return;
		toast.success(`${DELETE_NOUN[kind]} deleted`);
		pendingDelete = null;
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.reports)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<PageHeader
		title={routeLabels.reports}
		description="Reports for a scan or target, with templates, themes and branding"
	>
		{#snippet actions()}
			<Button
				size="sm"
				onclick={() => {
					generateTemplate = '';
					generateOpen = true;
				}}
				disabled={!projectId}
			>
				<PlusIcon class="size-4" />
				Generate report
			</Button>
		{/snippet}
	</PageHeader>

	<Tabs.Root
		class="gap-6"
		activationMode="manual"
		bind:value={
			() => activeTab,
			(v) => {
				if (v) requestTab(v as ReportTab);
			}
		}
	>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<ScrollArea orientation="horizontal" class="w-full max-w-full sm:w-fit">
				<Tabs.List class="w-max min-w-full">
					<Tabs.Trigger value="reports" class="gap-1.5">
						<FileTextIcon class="size-4" />
						Reports
						{#if reportsStore.reports.length && !stale}
							<span class="text-xs text-muted-foreground tabular-nums"
								>{reportsStore.reports.length}</span
							>
						{/if}
					</Tabs.Trigger>
					<Tabs.Trigger value="templates" class="gap-1.5">
						<LayoutTemplateIcon class="size-4" />
						Templates
						{#if reportsStore.templates.length}
							<span class="text-xs text-muted-foreground tabular-nums"
								>{reportsStore.templates.length}</span
							>
						{/if}
					</Tabs.Trigger>
					<Tabs.Trigger value="themes" class="gap-1.5">
						<PaletteIcon class="size-4" />
						Themes
						{#if reportCatalog.themes.length}
							<span class="text-xs text-muted-foreground tabular-nums"
								>{reportCatalog.themes.length}</span
							>
						{/if}
					</Tabs.Trigger>
					<Tabs.Trigger value="typefaces" class="gap-1.5">
						<TypeIcon class="size-4" />
						Typefaces
						{#if reportCatalog.catalog?.fonts.length}
							<span class="text-xs text-muted-foreground tabular-nums"
								>{reportCatalog.catalog.fonts.length}</span
							>
						{/if}
					</Tabs.Trigger>
					<Tabs.Trigger value="branding" class="gap-1.5">
						<StampIcon class="size-4" />
						Branding
					</Tabs.Trigger>
				</Tabs.List>
			</ScrollArea>

			{#if activeTab === 'templates'}
				<LoadingButton
					variant="outline"
					size="sm"
					loading={creatingTemplate}
					loadingLabel="Creating"
					disabled={!projectId || !reportCatalog.catalog}
					onclick={newTemplate}
				>
					<PlusIcon class="size-3.5" />
					New template
				</LoadingButton>
			{:else if activeTab === 'themes' || activeTab === 'typefaces'}
				<Hint text={isAdmin ? null : 'Editable by administrators'}>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<Button
								variant="outline"
								size="sm"
								disabled={!isAdmin}
								onclick={() =>
									activeTab === 'themes' ? (uploadOpen = true) : (fontUploadOpen = true)}
							>
								<UploadIcon class="size-3.5" />
								{activeTab === 'themes' ? 'Upload theme' : 'Upload typeface'}
							</Button>
						</span>
					{/snippet}
				</Hint>
			{/if}
		</div>

		{#if reportCatalog.loadError && (activeTab === 'templates' || activeTab === 'themes' || activeTab === 'typefaces')}
			<LoadNotice sections={['Report catalog']} busy={catalogRetrying} onRetry={retryCatalog} />
		{/if}

		<Tabs.Content value="reports">
			<Card.Root class="gap-0 overflow-hidden py-0">
				<div class="flex flex-wrap items-center gap-2 border-b px-4 py-3">
					<InputGroup.Root class="w-auto min-w-[240px] flex-1">
						<InputGroup.Addon>
							<SearchIcon />
						</InputGroup.Addon>
						<InputGroup.Input
							bind:value={search}
							placeholder="Search reports"
							aria-label="Search reports"
						/>
						{#if search}
							<InputGroup.Addon align="inline-end">
								<InputGroup.Button
									size="icon-xs"
									aria-label="Clear search"
									onclick={() => (search = '')}
								>
									<XIcon />
								</InputGroup.Button>
							</InputGroup.Addon>
						{/if}
					</InputGroup.Root>
				</div>

				<FilterChips
					chips={subjectChips}
					onRemove={(chip) => clearSubject(chip.id)}
					onClear={() => clearSubject()}
				/>

				{#if (reportsStore.isLoading && !reportsStore.reports.length) || (stale && !reportsStore.error)}
					<RowSkeleton rows={4} avatar="size-8 rounded-md" trailing="h-5 w-20 rounded-full" />
				{:else if reportsStore.error && !reportsStore.reports.length}
					<EmptyState
						icon={TriangleAlertIcon}
						title="Reports not loaded"
						description={reportsStore.error}
						class="rounded-none border-0 bg-transparent py-16"
					>
						<Button variant="outline" size="sm" onclick={() => reportsStore.fetch(projectId, true)}>
							Retry
						</Button>
					</EmptyState>
				{:else if !visibleReports.length}
					<EmptyState
						icon={FileTextIcon}
						title={filtered ? 'No matching reports' : 'No reports'}
						description={filtered ? undefined : 'Generate a report on a scan or a target.'}
						class="rounded-none border-0 bg-transparent py-16"
					>
						{#if !filtered}
							<Button
								size="sm"
								onclick={() => {
									generateTemplate = '';
									generateOpen = true;
								}}
								disabled={!projectId}
							>
								<PlusIcon class="size-4" />
								Generate report
							</Button>
						{/if}
						{#if search.trim()}
							<Button variant="outline" size="sm" onclick={() => (search = '')}>
								Clear search
							</Button>
						{/if}
						{#if subjectChips.length}
							<Button variant="outline" size="sm" onclick={() => clearSubject()}>
								Show all reports
							</Button>
						{/if}
					</EmptyState>
				{:else}
					<div
						class="flex items-center gap-3 border-b bg-muted/20 px-4 py-2 text-2xs font-medium tracking-wide text-muted-foreground uppercase"
					>
						<Checkbox
							checked={selectAllChecked === true}
							indeterminate={selectAllChecked === 'indeterminate'}
							onCheckedChange={toggleSelectAll}
							aria-label="Select all reports"
						/>
						<span>
							{filtered
								? `${visibleReports.length} of ${reportsStore.reports.length} reports`
								: 'Report'}
						</span>
					</div>
					{#each visibleReports as report (report.id)}
						<ReportRow
							{report}
							{projectId}
							isSelected={selectedIds.has(report.id)}
							onSelect={toggleReport}
							onRetry={(id) => reportsStore.retry(projectId, id)}
							onDelete={(id) => (pendingDelete = { kind: 'report', id, name: report.title })}
						/>
					{/each}
				{/if}
			</Card.Root>
		</Tabs.Content>

		<Tabs.Content value="templates">
			<TemplatesPanel
				templates={reportsStore.templates}
				loading={reportsStore.templatesLoading}
				error={reportsStore.templatesError}
				onRetry={() => reportsStore.fetchTemplates(projectId, true)}
				onDuplicate={duplicate}
				onDelete={(t) => (pendingDelete = { kind: 'template', id: t.id, name: t.name })}
				onGenerate={(t) => {
					generateTemplate = t.id;
					generateOpen = true;
				}}
			/>
		</Tabs.Content>

		<Tabs.Content value="themes">
			<ThemesPanel
				themes={reportCatalog.themes}
				onDelete={(t) => (pendingDelete = { kind: 'theme', id: t.slug, name: t.name })}
			/>
		</Tabs.Content>

		<Tabs.Content value="typefaces">
			<TypefacesPanel
				fonts={reportCatalog.catalog?.fonts ?? []}
				onDelete={(f) => (pendingDelete = { kind: 'typeface', id: f.slug, name: f.name })}
			/>
		</Tabs.Content>

		<Tabs.Content value="branding">
			{#key brandingResets}
				<DefaultsPanel onDirtyChange={(v) => (defaultsDirty = v)} />
			{/key}
		</Tabs.Content>
	</Tabs.Root>
</div>

{#if activeTab === 'reports'}
	<SelectionDeleteBar
		ids={[...selectedIds]}
		noun="report"
		removes="files"
		remove={(id) => reportsApi.remove(projectId, id)}
		onDone={() => {
			selectedIds.clear();
			void reportsStore.fetch(projectId, true);
		}}
		onClear={clearSelection}
	/>
{/if}

<GenerateDialog bind:open={generateOpen} {projectId} template={generateTemplate} />
<ThemeUploadDialog bind:open={uploadOpen} />
<FontUploadDialog bind:open={fontUploadOpen} />
<DeleteConfirmationDialog
	open={pendingDelete !== null}
	onOpenChange={(v) => {
		if (!v) pendingDelete = null;
	}}
	title={`Delete ${pendingDelete?.kind ?? 'report'}`}
	description={deleteDescription}
	isDeleting={deleting}
	onConfirm={confirmDelete}
/>

<UnsavedChangesDialog
	bind:open={leaveTabOpen}
	onOpenChange={(open) => {
		leaveTabOpen = open;
		if (!open) pendingTab = null;
	}}
	onConfirm={() => {
		const tab = pendingTab;
		pendingTab = null;
		defaultsDirty = false;
		brandingResets++;
		leaveTabOpen = false;
		if (tab) activeTab = tab;
	}}
/>
