<script lang="ts">
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Checkbox } from '$lib/components/ui/checkbox/index.js';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Skeleton } from '$lib/components/ui/skeleton/index.js';
	import FileTextIcon from '@lucide/svelte/icons/file-text';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import SearchIcon from '@lucide/svelte/icons/search';
	import EmptyState from '$lib/components/empty-state.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import SelectionActionBar from '$lib/components/selection-action-bar.svelte';
	import Trash2Icon from '@lucide/svelte/icons/trash-2';
	import ReportRow from '$lib/components/reports/report-row.svelte';
	import TemplateCard from '$lib/components/reports/template-card.svelte';
	import ThemeCard from '$lib/components/reports/theme-card.svelte';
	import ThemeUploadDialog from '$lib/components/reports/theme-upload-dialog.svelte';
	import FontUploadDialog from '$lib/components/reports/font-upload-dialog.svelte';
	import FontRow from '$lib/components/reports/font-row.svelte';
	import DefaultsPanel from '$lib/components/reports/defaults-panel.svelte';
	import GenerateDialog from '$lib/components/reports/generate-dialog.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { reports as reportsStore } from '$lib/stores/reports.svelte';
	import { reportCatalog } from '$lib/stores/report-catalog.svelte';
	import { reportsApi } from '$lib/api/reports';
	import { REPORT_TABS, routeLabels, type ReportTab } from '$lib/config/routes';
	import { toast } from 'svelte-sonner';
	import type { ReportTemplate } from '$lib/types/report';

	const DEFAULT_TAB: ReportTab = 'reports';
	const valid = new Set<string>(REPORT_TABS);
	const initial = page.url.searchParams.get('tab') ?? DEFAULT_TAB;

	let activeTab = $state<ReportTab>(valid.has(initial) ? (initial as ReportTab) : DEFAULT_TAB);
	let search = $state('');
	let generateOpen = $state(false);
	let uploadOpen = $state(false);
	let fontUploadOpen = $state(false);
	let pendingDelete = $state<{
		kind: 'report' | 'template' | 'theme' | 'typeface';
		id: string;
		name: string;
	} | null>(null);
	let bulkDeleteOpen = $state(false);
	let bulkDeleting = $state(false);

	const selectedIds = new SvelteSet<string>();

	const projectId = $derived(projectsStore.activeProject?.id ?? '');
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

	async function confirmBulkDelete() {
		const ids = [...selectedIds];
		if (!ids.length) return;
		bulkDeleting = true;
		const { ok, failed } = await reportsStore.removeMany(projectId, ids);
		bulkDeleting = false;
		bulkDeleteOpen = false;
		selectedIds.clear();
		if (ok > 0) toast.success(`Deleted ${ok} report${ok !== 1 ? 's' : ''}`);
		if (failed > 0) toast.error(`${failed} report${failed !== 1 ? 's' : ''} could not be deleted`);
	}

	$effect(() => {
		const id = projectId;
		if (!id) return;
		void reportsStore.fetch(id);
		void reportsStore.fetchTemplates(id);
		void reportCatalog.fetch();
	});

	$effect(() => {
		const tab = activeTab;
		if (!browser) return;
		const params = untrack(() => new URLSearchParams(page.url.searchParams));
		if (tab === DEFAULT_TAB) params.delete('tab');
		else params.set('tab', tab);
		const qs = params.toString();
		try {
			replaceState(qs ? `?${qs}` : location.pathname, {});
		} catch {
			// ignore
		}
	});

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
		if (created) toast.success(`${created.name} is ready to edit`);
	}

	const deleteDescription = $derived(
		pendingDelete?.kind === 'template'
			? `${pendingDelete.name} is removed. Reports already generated from it are unaffected.`
			: pendingDelete?.kind === 'theme'
				? `${pendingDelete.name} is removed. Reports already generated with it are unaffected.`
				: pendingDelete?.kind === 'typeface'
					? `${pendingDelete.name} and its font files are removed. A theme that names it falls back to a system face.`
					: `${pendingDelete?.name ?? 'This report'} and its downloaded files are removed.`
	);

	async function confirmDelete() {
		if (!pendingDelete) return;
		const { kind, id } = pendingDelete;
		if (kind === 'report') await reportsStore.remove(projectId, id);
		else if (kind === 'template') await reportsStore.removeTemplate(projectId, id);
		else if (kind === 'theme' || kind === 'typeface') {
			try {
				if (kind === 'theme') await reportsApi.deleteTheme(id);
				else await reportsApi.deleteFont(id);
				await reportCatalog.fetch(true);
			} catch (e) {
				toast.error(e instanceof Error ? e.message : `That ${kind} could not be deleted`);
			}
		}
		pendingDelete = null;
	}
</script>

<svelte:head><title>{routeLabels.reports} · reNgine</title></svelte:head>

<div class="space-y-6">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.reports}</h1>
			<p class="mt-1 text-sm text-muted-foreground">Documents generated from scan results</p>
		</div>
		<Button onclick={() => (generateOpen = true)} disabled={!projectId}>
			<PlusIcon class="mr-1.5 size-4" />
			Generate report
		</Button>
	</div>

	<Tabs.Root value={activeTab} onValueChange={(v) => v && (activeTab = v as ReportTab)}>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<Tabs.List class="w-full sm:w-fit">
				<Tabs.Trigger value="reports">
					Reports
					{#if reportsStore.reports.length}
						<span class="ml-1.5 text-muted-foreground">{reportsStore.reports.length}</span>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="templates">
					Templates
					{#if reportsStore.templates.length}
						<span class="ml-1.5 text-muted-foreground">{reportsStore.templates.length}</span>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="themes">
					Themes
					{#if reportCatalog.themes.length}
						<span class="ml-1.5 text-muted-foreground">{reportCatalog.themes.length}</span>
					{/if}
				</Tabs.Trigger>
				<Tabs.Trigger value="defaults">Defaults</Tabs.Trigger>
			</Tabs.List>

			{#if activeTab === 'reports'}
				<div class="relative w-full sm:w-64">
					<SearchIcon
						class="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
					/>
					<Input bind:value={search} placeholder="Search reports…" class="h-9 pl-8" />
				</div>
			{:else if activeTab === 'themes'}
				<div class="flex gap-2">
					<Button variant="outline" size="sm" onclick={() => (fontUploadOpen = true)}>
						<UploadIcon class="mr-1.5 size-3.5" />
						Upload a typeface
					</Button>
					<Button variant="outline" size="sm" onclick={() => (uploadOpen = true)}>
						<UploadIcon class="mr-1.5 size-3.5" />
						Upload a theme
					</Button>
				</div>
			{/if}
		</div>

		<Tabs.Content value="reports" class="mt-5">
			{#if reportsStore.isLoading && !reportsStore.reports.length}
				<div class="space-y-2">
					{#each [1, 2, 3] as n (n)}<Skeleton class="h-16 w-full" />{/each}
				</div>
			{:else if !visibleReports.length}
				<EmptyState
					icon={FileTextIcon}
					title="No reports yet"
					description="Generate a report from a finished scan. Generation runs in the background."
				/>
			{:else}
				<Card.Root class="gap-0 py-0">
					<div
						class="flex items-center gap-3 border-b border-border bg-muted/30 px-4 py-2 text-xs font-medium tracking-wider text-muted-foreground uppercase"
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
							selectable
							isSelected={selectedIds.has(report.id)}
							onSelect={toggleReport}
							onRetry={(id) => reportsStore.retry(projectId, id)}
							onDelete={(id) => (pendingDelete = { kind: 'report', id, name: report.title })}
						/>
					{/each}
				</Card.Root>
			{/if}
		</Tabs.Content>

		<Tabs.Content value="templates" class="mt-5">
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each reportsStore.templates as template (template.id)}
					<TemplateCard
						{template}
						onDuplicate={duplicate}
						onDelete={(t) => (pendingDelete = { kind: 'template', id: t.id, name: t.name })}
						onGenerate={() => (generateOpen = true)}
					/>
				{/each}
			</div>
		</Tabs.Content>

		<Tabs.Content value="themes" class="mt-5">
			<div class="space-y-6">
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{#each reportCatalog.themes as theme (theme.slug)}
						<ThemeCard
							{theme}
							onDelete={(slug) => (pendingDelete = { kind: 'theme', id: slug, name: theme.name })}
						/>
					{/each}
				</div>

				<div class="space-y-2">
					<div>
						<h2 class="text-base font-semibold">Typefaces</h2>
						<p class="text-xs text-muted-foreground">
							Typefaces a theme can name for its headings, body and code. Files are stored on this
							instance. A report never fetches a font.
						</p>
					</div>
					<Card.Root class="gap-0 py-0">
						{#each reportCatalog.catalog?.fonts ?? [] as font (font.slug)}
							<FontRow
								{font}
								onDelete={(slug) =>
									(pendingDelete = { kind: 'typeface', id: slug, name: font.name })}
							/>
						{/each}
					</Card.Root>
				</div>
			</div>
		</Tabs.Content>

		<Tabs.Content value="defaults" class="mt-5">
			<DefaultsPanel />
		</Tabs.Content>
	</Tabs.Root>
</div>

{#if activeTab === 'reports'}
	<SelectionActionBar {selectedCount} noun="report" onClear={clearSelection}>
		<Button
			variant="ghost"
			size="sm"
			class="gap-2 font-medium text-destructive hover:bg-destructive/10 hover:text-destructive"
			onclick={() => (bulkDeleteOpen = true)}
		>
			<Trash2Icon class="h-3.5 w-3.5" />
			Delete
		</Button>
	</SelectionActionBar>
{/if}

<DeleteConfirmationDialog
	open={bulkDeleteOpen}
	onOpenChange={(v) => (bulkDeleteOpen = v)}
	title="Delete {selectedCount} report{selectedCount !== 1 ? 's' : ''}?"
	description="The selected reports and their downloaded files are removed."
	confirmLabel="Delete {selectedCount}"
	isDeleting={bulkDeleting}
	onConfirm={confirmBulkDelete}
/>

<GenerateDialog bind:open={generateOpen} {projectId} />
<ThemeUploadDialog bind:open={uploadOpen} />
<FontUploadDialog bind:open={fontUploadOpen} />
<DeleteConfirmationDialog
	open={pendingDelete !== null}
	onOpenChange={(v) => {
		if (!v) pendingDelete = null;
	}}
	title={`Delete this ${pendingDelete?.kind ?? 'report'}?`}
	description={deleteDescription}
	onConfirm={confirmDelete}
/>
