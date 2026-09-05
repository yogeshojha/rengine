<script lang="ts">
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import AlertCircle from '@lucide/svelte/icons/alert-circle';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import ListChecks from '@lucide/svelte/icons/list-checks';
	import Search from '@lucide/svelte/icons/search';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import SearchX from '@lucide/svelte/icons/search-x';

	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { proxiesStore } from '$lib/stores/proxies.svelte';
	import { ROUTES } from '$lib/config/routes';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as Alert from '$lib/components/ui/alert';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as Select from '$lib/components/ui/select';
	import EmptyState from '@/components/empty-state.svelte';
	import ContextListCard from '$lib/components/contexts/context-list-card.svelte';
	import ContextFacets from '$lib/components/contexts/context-facets.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import SelectionActionBar from '@/components/selection-action-bar.svelte';
	import { contextFacets, facetLine } from '$lib/components/contexts/context-summary';
	import { CONTEXT_TEMPLATES, templateDraft } from '$lib/components/contexts/context-templates';
	import type { ScanContextRead } from '$lib/types/scan-context';

	type SortKey = 'recent' | 'name' | 'usage';
	const SORT_LABELS: Record<SortKey, string> = {
		recent: 'Recently used',
		name: 'Name',
		usage: 'Most used'
	};

	let isRefreshing = $state(false);
	let showLaunch = $state(false);
	let launchContextId = $state('');
	let contextToDelete = $state<ScanContextRead | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let deleteMode = $state<'single' | 'bulk'>('single');
	const selectedIds = new SvelteSet<string>();
	let query = $state('');
	let sortKey = $state<SortKey>('recent');

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (scanContextsStore.fetchedProjectId !== project.id) {
					selectedIds.clear();
					scanContextsStore.fetchContexts(project.id);
				}
			});
		}
	});

	$effect(() => {
		if (!proxiesStore.hasFetched) proxiesStore.fetch();
	});

	function proxyName(context: ScanContextRead): string | null {
		if (!context.proxy_id) return null;
		return proxiesStore.proxies.find((p) => p.id === context.proxy_id)?.name ?? null;
	}

	function lastUsed(context: ScanContextRead): number {
		return context.last_used_at ? Date.parse(context.last_used_at) : 0;
	}

	function compare(a: ScanContextRead, b: ScanContextRead): number {
		if (sortKey === 'name') return a.name.localeCompare(b.name);
		if (sortKey === 'usage') {
			return (b.usage?.scans ?? 0) - (a.usage?.scans ?? 0) || a.name.localeCompare(b.name);
		}
		return (
			lastUsed(b) - lastUsed(a) ||
			Date.parse(b.updated_at) - Date.parse(a.updated_at) ||
			a.name.localeCompare(b.name)
		);
	}

	const visibleContexts = $derived.by(() => {
		const term = query.trim().toLowerCase();
		const list = scanContextsStore.contexts.filter((context) => {
			if (!term) return true;
			if (context.name.toLowerCase().includes(term)) return true;
			if ((context.description ?? '').toLowerCase().includes(term)) return true;
			return contextFacets(context, proxyName(context)).some(
				(f) => f.set && f.value.toLowerCase().includes(term)
			);
		});
		return list.sort(compare);
	});

	function handleNewContext(template?: string) {
		const project = projectsStore.activeProject;
		if (!project) {
			toast.error('No active project selected');
			return;
		}
		goto(ROUTES.newContext(project.id, template));
	}

	async function handleDuplicate(context: ScanContextRead) {
		const project = projectsStore.activeProject;
		if (!project || !context.id) return;
		const dup = await scanContextsStore.duplicateContext(context.id, project.id);
		if (dup) toast.success(`Duplicated "${context.name}"`);
		else toast.error(scanContextsStore.error ?? 'Failed to duplicate context');
	}

	function toggleSelect(id: string) {
		if (selectedIds.has(id)) selectedIds.delete(id);
		else selectedIds.add(id);
	}

	function clearSelection() {
		selectedIds.clear();
	}

	function toggleSelectAll() {
		const all = scanContextsStore.contexts;
		if (selectedIds.size >= all.length) selectedIds.clear();
		else for (const c of all) selectedIds.add(c.id);
	}

	function requestBulkDelete() {
		if (selectedIds.size === 0) return;
		deleteMode = 'bulk';
		showDeleteDialog = true;
	}

	async function confirmDelete() {
		isDeleting = true;
		try {
			if (deleteMode === 'single') {
				if (!contextToDelete?.id) return;
				const ok = await scanContextsStore.deleteContext(
					contextToDelete.id,
					contextToDelete.project_id
				);
				if (ok) {
					toast.success(`Deleted "${contextToDelete.name}"`);
					selectedIds.delete(contextToDelete.id);
					showDeleteDialog = false;
					contextToDelete = null;
				} else {
					toast.error(scanContextsStore.error ?? 'Failed to delete context');
				}
				return;
			}

			const byId = new Map(scanContextsStore.contexts.map((c) => [c.id, c]));
			const ids = Array.from(selectedIds);
			let failed = 0;
			let lastError = '';
			for (const id of ids) {
				const ok = await scanContextsStore.deleteContext(id, byId.get(id)?.project_id);
				if (ok) selectedIds.delete(id);
				else {
					failed++;
					lastError = scanContextsStore.error ?? '';
				}
			}
			const deleted = ids.length - failed;
			if (deleted) toast.success(`${deleted} context${deleted !== 1 ? 's' : ''} deleted`);
			if (failed) {
				toast.error(
					`${failed} context${failed !== 1 ? 's' : ''} kept${lastError ? ` — ${lastError}` : ''}`
				);
			}
			showDeleteDialog = false;
		} finally {
			isDeleting = false;
		}
	}

	const deleteTitle = $derived(
		deleteMode === 'single'
			? 'Delete this context?'
			: `Delete ${selectedIds.size} context${selectedIds.size !== 1 ? 's' : ''}?`
	);
	const deleteDescription = $derived(
		deleteMode === 'single'
			? 'Removes this context from the project. Completed scans and their results are unaffected. This action cannot be undone.'
			: 'Removes the selected contexts from the project. Contexts referenced by a schedule or a running scan are skipped. Completed scans and their results are unaffected. This action cannot be undone.'
	);

	async function handleRefresh() {
		const project = projectsStore.activeProject;
		if (!project) return;
		isRefreshing = true;
		try {
			await scanContextsStore.fetchContexts(project.id);
			if (scanContextsStore.error) toast.error(scanContextsStore.error);
			else toast.success('Contexts refreshed');
		} finally {
			isRefreshing = false;
		}
	}

	const total = $derived(scanContextsStore.contexts.length);
</script>

<div class="space-y-6">
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div class="max-w-2xl">
			<h1 class="text-2xl font-semibold tracking-tight">Scan Contexts</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				Credentials, rate limits, scope rules and proxy settings applied when a scan runs. Contexts
				are optional and reusable across engines and targets.
			</p>
		</div>
		<div class="flex items-center gap-2">
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9"
				aria-label="Refresh"
				onclick={handleRefresh}
				disabled={isRefreshing}
			>
				<RefreshCw class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
			</Button>
			<Button class="gap-2" onclick={() => handleNewContext()}>
				<Plus class="h-4 w-4" />
				New context
			</Button>
		</div>
	</div>

	{#if scanContextsStore.error && !scanContextsStore.isLoading}
		<Alert.Root variant="destructive">
			<AlertCircle />
			<Alert.Title>Couldn't load scan contexts</Alert.Title>
			<Alert.Description class="flex flex-wrap items-center justify-between gap-3">
				<span>{scanContextsStore.error}</span>
				<Button
					variant="outline"
					size="sm"
					class="gap-1.5"
					onclick={handleRefresh}
					disabled={isRefreshing}
				>
					<RefreshCw class="h-3.5 w-3.5 {isRefreshing ? 'animate-spin' : ''}" />
					Retry
				</Button>
			</Alert.Description>
		</Alert.Root>
	{/if}

	{#if scanContextsStore.isLoading}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<div class="flex flex-col gap-3 rounded-xl border border-border p-4">
					<Skeleton class="h-[18px] w-40" />
					<Skeleton class="h-3.5 w-4/5" />
					<Skeleton class="mt-2 h-24 w-full" />
					<Skeleton class="h-6 w-full" />
				</div>
			{/each}
		</div>
	{:else if total === 0}
		<section class="rounded-xl border border-border bg-muted/20 p-6 sm:p-8">
			<div class="max-w-xl">
				<h2 class="text-lg font-semibold tracking-tight">Create your first context</h2>
				<p class="mt-1 text-sm text-muted-foreground">
					A context controls how a scan reaches its target: credentials, headers, rate limits, scope
					and proxy. Start from a template or build one from scratch.
				</p>
			</div>
			<div class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				{#each CONTEXT_TEMPLATES as template (template.key)}
					{@const draft = templateDraft(template.key)}
					{@const line = facetLine(draft)}
					<button
						type="button"
						class="group flex flex-col gap-3 rounded-lg border border-border bg-card p-4 text-left transition-colors hover:border-foreground/25 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
						onclick={() => handleNewContext(template.key)}
					>
						<span class="flex items-start justify-between gap-2">
							<span class="text-sm font-medium">{template.title}</span>
							<ArrowRight
								size={14}
								class="mt-0.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
							/>
						</span>
						<span class="text-xs text-muted-foreground">{template.description}</span>
						<ContextFacets context={draft} variant="inline" class="mt-auto text-[11px]" />
						<span class="sr-only">{line}</span>
					</button>
				{/each}
			</div>
		</section>
	{:else}
		<div class="flex flex-wrap items-center gap-2">
			<InputGroup.Root class="h-9 w-full sm:max-w-xs">
				<InputGroup.Addon>
					<Search />
				</InputGroup.Addon>
				<InputGroup.Input bind:value={query} placeholder="Search contexts, auth, scope…" />
			</InputGroup.Root>
			<Select.Root
				type="single"
				value={sortKey}
				onValueChange={(v) => v && (sortKey = v as SortKey)}
			>
				<Select.Trigger class="h-9 w-[170px] gap-2 text-sm" aria-label="Sort contexts">
					<ArrowUpDown size={14} class="text-muted-foreground" />
					{SORT_LABELS[sortKey]}
				</Select.Trigger>
				<Select.Content>
					{#each Object.entries(SORT_LABELS) as [key, label] (key)}
						<Select.Item value={key} {label}>{label}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<span class="ml-auto text-xs text-muted-foreground tabular-nums">
				{#if query.trim()}
					{visibleContexts.length} of {total} context{total === 1 ? '' : 's'}
				{:else}
					{total} context{total === 1 ? '' : 's'}
				{/if}
			</span>
		</div>

		{#if visibleContexts.length === 0}
			<EmptyState
				icon={SearchX}
				title="No contexts match"
				description="Adjust your search or clear it to see all contexts."
				compact
			>
				<Button variant="outline" size="sm" onclick={() => (query = '')}>Clear search</Button>
			</EmptyState>
		{:else}
			<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
				{#each visibleContexts as context (context.id)}
					<ContextListCard
						{context}
						proxyName={proxyName(context)}
						isSelected={selectedIds.has(context.id)}
						onSelect={() => toggleSelect(context.id)}
						onEdit={() => goto(ROUTES.context(context.id))}
						onRun={() => {
							launchContextId = context.id;
							showLaunch = true;
						}}
						onDuplicate={() => handleDuplicate(context)}
						onDelete={() => {
							deleteMode = 'single';
							contextToDelete = context;
							showDeleteDialog = true;
						}}
					/>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<SelectionActionBar selectedCount={selectedIds.size} noun="context" onClear={clearSelection}>
	<Button variant="ghost" size="sm" class="gap-2 font-medium" onclick={toggleSelectAll}>
		<ListChecks class="h-3.5 w-3.5 text-muted-foreground" />
		{selectedIds.size >= total ? 'Deselect all' : 'Select all'}
	</Button>
	<Button
		variant="ghost"
		size="sm"
		class="gap-2 font-medium text-destructive hover:bg-destructive/10 hover:text-destructive"
		onclick={requestBulkDelete}
	>
		<Trash2 class="h-3.5 w-3.5" />
		Delete
	</Button>
</SelectionActionBar>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title={deleteTitle}
	description={deleteDescription}
	{isDeleting}
	onOpenChange={(open) => {
		showDeleteDialog = open;
		if (!open) contextToDelete = null;
	}}
	onConfirm={confirmDelete}
/>

<LaunchDialog bind:open={showLaunch} presetContextId={launchContextId} />
