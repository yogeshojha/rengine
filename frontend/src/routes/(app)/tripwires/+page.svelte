<script lang="ts">
	import { untrack } from 'svelte';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import Plus from '@lucide/svelte/icons/plus';
	import Zap from '@lucide/svelte/icons/zap';
	import LayoutTemplate from '@lucide/svelte/icons/layout-template';
	import { toast } from 'svelte-sonner';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import RowSkeleton from '$lib/components/skeleton/row-skeleton.svelte';
	import TripwiresTable from '$lib/components/tripwires/tripwires-table.svelte';
	import TripwireWizard, {
		type TripwireDraft
	} from '$lib/components/tripwires/tripwire-wizard.svelte';
	import TripwireHistorySheet from '$lib/components/tripwires/tripwire-history-sheet.svelte';
	import TemplateGrid from '$lib/components/tripwires/template-grid.svelte';
	import TemplateSheet from '$lib/components/tripwires/template-sheet.svelte';
	import { tripwiresApi } from '$lib/api/tripwires';
	import { tripwiresStore } from '$lib/stores/tripwires.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { RECENT_DAYS, RUN_PARAM, TRIPWIRE_PARAM } from '$lib/config/tripwires';
	import { ROUTES, routeLabels } from '$lib/config/routes';
	import type { Tripwire, TripwireTemplate } from '$lib/types/tripwire';
	import { pageTitle } from '$lib/utilities/page-title';

	const TABS = [
		{ key: 'all', label: 'All' },
		{ key: 'fired', label: `Fired in ${RECENT_DAYS} days` },
		{ key: 'paused', label: 'Paused' }
	];

	let tab = $state('all');
	let wizardOpen = $state(false);
	let editing = $state<Tripwire | null>(null);
	let draft = $state<TripwireDraft | null>(null);
	let templatesOpen = $state(false);
	let historyId = $state<string | null>(null);
	let focusRunId = $state<string | null>(null);
	let pending = $state<Tripwire | null>(null);
	let deleting = $state(false);
	let landed = $state<string | null>(null);

	let project = $derived(projectsStore.activeProject);
	let projectId = $derived(project?.id ?? '');
	let projectSlug = $derived(project?.slug ?? '');
	let tripwires = $derived(tripwiresStore.tripwires);
	let catalog = $derived(tripwiresStore.catalog);
	let catalogFailed = $state(false);
	let history = $derived(historyId ? (tripwires.find((t) => t.id === historyId) ?? null) : null);
	let counts = $derived({
		all: tripwires.length,
		fired: tripwires.filter((t) => t.recent_fired > 0).length,
		paused: tripwires.filter((t) => !t.enabled).length
	});
	let shown = $derived(
		tab === 'fired'
			? tripwires.filter((t) => t.recent_fired > 0)
			: tab === 'paused'
				? tripwires.filter((t) => !t.enabled)
				: tripwires
	);

	$effect(() => {
		const id = projectId;
		if (!id || !projectsStore.hasFetched) return;
		untrack(() => {
			void tripwiresStore.loadCatalog().then((c) => (catalogFailed = c === null));
			if (tripwiresStore.fetchedProjectId !== id) void tripwiresStore.fetch(id);
		});
	});

	const SETTLE_DELAY_MS = 4000;

	$effect(() => {
		const tick = liveScans.completedTick;
		if (!tick || !projectId) return;
		const timer = setTimeout(() => void tripwiresStore.refresh(), SETTLE_DELAY_MS);
		return () => clearTimeout(timer);
	});

	$effect(() => {
		const runId = page.url.searchParams.get(RUN_PARAM);
		const tripwireId = page.url.searchParams.get(TRIPWIRE_PARAM);
		const id = projectId;
		const key = `${runId ?? ''}|${tripwireId ?? ''}`;
		if (!id || landed === key || (!runId && !tripwireId)) return;
		untrack(() => {
			landed = key;
			if (runId) void land(runId, id);
			else if (tripwireId) historyId = tripwireId;
		});
	});

	async function land(runId: string, id: string) {
		try {
			const run = await tripwiresApi.run(runId, id);
			focusRunId = run.id;
			historyId = run.tripwire_id;
			if (tripwiresStore.fetchedProjectId !== id) await tripwiresStore.fetch(id);
		} catch {
			toast.error('Check not found');
		}
	}

	function openNew(seed: TripwireDraft | null = null) {
		editing = null;
		draft = seed;
		wizardOpen = true;
	}

	function openEdit(tripwire: Tripwire) {
		editing = tripwire;
		draft = null;
		wizardOpen = true;
	}

	function fromTemplate(template: TripwireTemplate) {
		openNew({
			name: template.name,
			dimension: template.dimension,
			query: template.query,
			fire_on: template.fire_on,
			trigger: template.trigger
		});
	}

	function openHistory(tripwire: Tripwire) {
		focusRunId = null;
		historyId = tripwire.id;
	}

	function closeHistory() {
		historyId = null;
		focusRunId = null;
		if (page.url.searchParams.has(RUN_PARAM) || page.url.searchParams.has(TRIPWIRE_PARAM)) {
			replaceState(ROUTES.tripwires(), {});
		}
	}

	async function toggle(tripwire: Tripwire, enabled: boolean) {
		try {
			const saved = await tripwiresApi.update(tripwire.id, projectId, { enabled });
			tripwiresStore.upsert(saved);
			toast.success(enabled ? `${saved.name} resumed` : `${saved.name} paused`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Tripwire not updated');
		}
	}

	async function confirmDelete() {
		if (!pending) return;
		deleting = true;
		try {
			await tripwiresApi.remove(pending.id, projectId);
			tripwiresStore.remove(pending.id);
			if (historyId === pending.id) closeHistory();
			toast.success(`${pending.name} deleted`);
			pending = null;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Tripwire not deleted');
		} finally {
			deleting = false;
		}
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.tripwires)}</title></svelte:head>

<div class="space-y-6">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="min-w-0">
			<h1 class="text-2xl font-semibold tracking-tight">{routeLabels.tripwires}</h1>
			<p class="mt-1 text-sm text-muted-foreground">
				A saved query that notifies or starts a scan when a result matches it
			</p>
		</div>
		<div class="flex flex-wrap items-center gap-2">
			<Button variant="outline" size="sm" onclick={() => (templatesOpen = true)}>
				<LayoutTemplate class="size-4" />
				Templates
			</Button>
			<Button size="sm" onclick={() => openNew()}>
				<Plus class="size-4" />
				New tripwire
			</Button>
		</div>
	</div>

	{#if tripwiresStore.error && !tripwiresStore.isLoading}
		<div
			class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
		>
			{tripwiresStore.error}
		</div>
	{/if}

	{#if tripwiresStore.isLoading && tripwires.length === 0}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<RowSkeleton rows={5} class="px-4" />
		</Card.Root>
	{:else if tripwires.length === 0 && !tripwiresStore.error}
		<Card.Root class="gap-0 py-0">
			<div class="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
				<div class="flex items-center gap-3">
					<div class="flex size-9 items-center justify-center rounded-lg bg-muted">
						<Zap class="size-4 text-muted-foreground" />
					</div>
					<span class="text-sm font-semibold">No tripwires</span>
				</div>
			</div>
			<div class="px-5 py-5">
				{#if catalog}
					<TemplateGrid
						templates={catalog.templates}
						groups={catalog.template_groups}
						columns="sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
						onPick={fromTemplate}
					/>
				{:else if catalogFailed}
					<p class="text-sm text-muted-foreground">Templates not loaded.</p>
				{:else}
					<RowSkeleton rows={4} />
				{/if}
			</div>
		</Card.Root>
	{:else}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<div class="border-b px-2">
				<CountTabs tabs={TABS} value={tab} {counts} onChange={(k) => (tab = k)} />
			</div>
			{#if shown.length === 0}
				<EmptyState
					icon={Zap}
					title={tab === 'paused'
						? 'No paused tripwires'
						: `No tripwire fired in ${RECENT_DAYS} days`}
					class="rounded-none border-0 bg-transparent py-16"
				/>
			{:else}
				<TripwiresTable
					tripwires={shown}
					onOpen={openHistory}
					onEdit={openEdit}
					onToggle={toggle}
					onDelete={(t) => (pending = t)}
				/>
			{/if}
		</Card.Root>
	{/if}
</div>

<TripwireWizard
	open={wizardOpen}
	{projectId}
	{projectSlug}
	tripwire={editing}
	{draft}
	onOpenChange={(v) => (wizardOpen = v)}
	onSaved={(t) => tripwiresStore.upsert(t)}
/>

<TripwireHistorySheet
	tripwire={history}
	{projectId}
	{focusRunId}
	onOpenChange={(v) => {
		if (!v) closeHistory();
	}}
	onEdit={openEdit}
	onToggle={toggle}
/>

<TemplateSheet
	open={templatesOpen}
	{catalog}
	onOpenChange={(v) => (templatesOpen = v)}
	onPick={fromTemplate}
/>

<ConfirmDialog
	open={pending !== null}
	title={pending ? `Delete ${pending.name}` : 'Delete tripwire'}
	description="The tripwire and its check history are removed."
	confirmLabel="Delete"
	loadingLabel="Deleting"
	loading={deleting}
	destructive
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirmDelete}
/>
