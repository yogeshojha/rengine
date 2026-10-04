<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { untrack } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import ListChecks from '@lucide/svelte/icons/list-checks';
	import Search from '@lucide/svelte/icons/search';
	import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
	import SearchX from '@lucide/svelte/icons/search-x';

	import { scanContextsApi } from '$lib/api/scan-contexts';
	import { scanContextsStore } from '$lib/stores/scan-contexts.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { proxiesStore } from '$lib/stores/proxies.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import * as InputGroup from '$lib/components/ui/input-group';
	import * as Select from '$lib/components/ui/select';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import ContextListCard from '$lib/components/contexts/context-list-card.svelte';
	import LaunchDialog from '$lib/components/scans/launch/launch-dialog.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import { contextFacets } from '$lib/components/contexts/context-summary';
	import { CONTEXT_TEMPLATES, templateFacet } from '$lib/components/contexts/context-templates';
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
		if (auth.user?.is_superuser && !proxiesStore.hasFetched) untrack(() => proxiesStore.fetch());
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
			toast.error('No active project');
			return;
		}
		goto(ROUTES.newContext(template));
	}

	async function handleDuplicate(context: ScanContextRead) {
		const project = projectsStore.activeProject;
		if (!project || !context.id) return;
		const dup = await scanContextsStore.duplicateContext(context.id, project.id);
		if (dup) toast.success('Context duplicated');
		else toast.error(scanContextsStore.error ?? 'Context not duplicated');
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

	async function confirmDelete() {
		if (!contextToDelete?.id) return;
		isDeleting = true;
		try {
			const ok = await scanContextsStore.deleteContext(
				contextToDelete.id,
				contextToDelete.project_id
			);
			if (ok) {
				toast.success('Context deleted');
				selectedIds.delete(contextToDelete.id);
				showDeleteDialog = false;
				contextToDelete = null;
			} else {
				toast.error(scanContextsStore.error ?? 'Context not deleted');
			}
		} finally {
			isDeleting = false;
		}
	}

	async function handleRefresh() {
		const project = projectsStore.activeProject;
		if (!project) return;
		isRefreshing = true;
		try {
			await scanContextsStore.fetchContexts(project.id);
			if (scanContextsStore.error) toast.error(scanContextsStore.error);
		} finally {
			isRefreshing = false;
		}
	}

	const total = $derived(scanContextsStore.contexts.length);
	const loaded = $derived(
		Boolean(projectsStore.activeProject) &&
			scanContextsStore.fetchedProjectId === projectsStore.activeProject?.id
	);
	const loadFailed = $derived(
		!loaded && Boolean(scanContextsStore.error) && !scanContextsStore.isLoading
	);
</script>

<svelte:head><title>{pageTitle(routeLabels.contexts)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="min-w-0">
			<h1 class="text-2xl font-semibold tracking-tight">Scan contexts</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				Credentials, rate limits, scope rules and proxy settings for a scan
			</p>
		</div>
		<div class="flex flex-wrap items-center gap-2">
			<Hint text="Refresh">
				{#snippet child(props)}
					<Button
						{...props}
						variant="outline"
						size="icon-sm"
						aria-label="Refresh"
						onclick={handleRefresh}
						disabled={isRefreshing}
					>
						<RefreshCw class="size-4 {isRefreshing ? 'animate-spin' : ''}" />
					</Button>
				{/snippet}
			</Hint>
			<Button size="sm" onclick={() => handleNewContext()}>
				<Plus class="size-4" />
				New context
			</Button>
		</div>
	</div>

	{#if loadFailed}
		<EmptyState
			icon={TriangleAlert}
			title="Scan contexts not loaded"
			description={scanContextsStore.error ?? undefined}
		>
			<Button variant="outline" size="sm" onclick={handleRefresh}>Retry</Button>
		</EmptyState>
	{:else if !loaded}
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
				<h2 class="text-lg font-semibold tracking-tight">No scan contexts</h2>
			</div>
			<div class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				{#each CONTEXT_TEMPLATES as template (template.key)}
					{@const facet = templateFacet(template)}
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
						{#if facet}
							<p class="mt-auto text-2xs leading-relaxed text-foreground">{facet}</p>
						{/if}
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
			<EmptyState icon={SearchX} title="No contexts match" compact>
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
							contextToDelete = context;
							showDeleteDialog = true;
						}}
					/>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<SelectionDeleteBar
	ids={[...selectedIds]}
	noun="context"
	remove={(id) => scanContextsApi.remove(id, projectsStore.activeProject?.id ?? '')}
	onDone={() => {
		selectedIds.clear();
		const project = projectsStore.activeProject;
		if (project) void scanContextsStore.fetchContexts(project.id);
	}}
	onClear={clearSelection}
>
	<Button variant="ghost" size="sm" class="font-medium" onclick={toggleSelectAll}>
		<ListChecks class="h-3.5 w-3.5 text-muted-foreground" />
		{selectedIds.size >= total ? 'Deselect all' : 'Select all'}
	</Button>
</SelectionDeleteBar>

<DeleteConfirmationDialog
	bind:open={showDeleteDialog}
	title="Delete context"
	description={`Context ${contextToDelete?.name ?? ''} is removed.`}
	{isDeleting}
	onOpenChange={(open) => {
		showDeleteDialog = open;
		if (!open) contextToDelete = null;
	}}
	onConfirm={confirmDelete}
/>

<LaunchDialog bind:open={showLaunch} presetContextId={launchContextId} />
