<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { plural } from '$lib/utilities/strings';
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import SquareKanbanIcon from '@lucide/svelte/icons/square-kanban';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import CountTabs from '$lib/components/count-tabs.svelte';
	import ConfirmDialog from '$lib/components/confirm-dialog.svelte';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import TrackersTable from '$lib/components/issue-trackers/trackers-table.svelte';
	import RoutesTable from '$lib/components/issue-trackers/routes-table.svelte';
	import IssuesTable from '$lib/components/issue-trackers/issues-table.svelte';
	import FilterChips from '$lib/components/scans/results/table/filter-chips.svelte';
	import ConnectSheet from '$lib/components/issue-trackers/connect-sheet.svelte';
	import RouteDialog from '$lib/components/issue-trackers/route-dialog.svelte';
	import { issueTrackersApi } from '$lib/api/issue-trackers';
	import { issueTrackers } from '$lib/stores/issue-trackers.svelte';
	import { auth } from '$lib/stores/auth.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import {
		ISSUE_TRACKER_TABS,
		TRACKER_PARAM,
		routeLabels,
		type IssueTrackerTab
	} from '$lib/config/routes';
	import { FilingState, MAX_TRACKERS } from '$lib/config/issue-trackers';
	import type { IssueTracker, TrackedIssue, TrackerRoute } from '$lib/types/issue-tracker';

	const POLL_MS = 15_000;
	const TAB_LABELS: Record<IssueTrackerTab, string> = {
		issues: 'Issues',
		trackers: 'Trackers',
		routes: 'Routes'
	};
	const TABS = ISSUE_TRACKER_TABS.map((key) => ({ key, label: TAB_LABELS[key] }));
	const validTabs = new Set<string>(ISSUE_TRACKER_TABS);

	type Pending =
		| { kind: 'tracker'; tracker: IssueTracker }
		| { kind: 'route'; route: TrackerRoute }
		| { kind: 'issue'; issue: TrackedIssue };

	const initialTab = page.url.searchParams.get('tab') ?? '';
	let activeTab = $state<IssueTrackerTab | null>(
		validTabs.has(initialTab) ? (initialTab as IssueTrackerTab) : null
	);
	let trackerFilter = $state<string | null>(page.url.searchParams.get(TRACKER_PARAM));
	let connectOpen = $state(false);
	let editing = $state<IssueTracker | null>(null);
	let routeOpen = $state(false);
	let editingRoute = $state<TrackerRoute | null>(null);
	let testing = $state<string | null>(null);
	let pending = $state<Pending | null>(null);
	let removing = $state(false);

	const canAdmin = $derived(auth.user?.is_superuser ?? false);
	const project = $derived(projectsStore.activeProject);
	const trackers = $derived(issueTrackers.trackers);
	const tab = $derived<IssueTrackerTab>(
		activeTab ?? (issueTrackers.loaded && !trackers.length ? 'trackers' : 'issues')
	);
	const atLimit = $derived(trackers.length >= MAX_TRACKERS);
	const filtered = $derived(trackers.find((t) => t.id === trackerFilter) ?? null);
	const shownIssues = $derived(
		filtered
			? issueTrackers.issues.filter((i) => i.tracker_id === filtered.id)
			: issueTrackers.issues
	);
	const filterChips = $derived(filtered ? [{ id: filtered.id, label: filtered.name }] : []);
	const counts = $derived({
		issues: shownIssues.length,
		trackers: trackers.length,
		routes: issueTrackers.routes.length
	});
	const inFlight = $derived(issueTrackers.issues.some((i) => i.state === FilingState.PENDING));

	$effect(() => {
		const id = project?.id;
		untrack(() => {
			void issueTrackers.load();
			if (id) void issueTrackers.loadProject(id);
		});
	});

	$effect(() => {
		if (!browser || !activeTab) return;
		const url = new URL(page.url);
		const tracker = trackerFilter ?? '';
		if (
			url.searchParams.get('tab') === activeTab &&
			(url.searchParams.get(TRACKER_PARAM) ?? '') === tracker
		)
			return;
		url.searchParams.set('tab', activeTab);
		if (tracker) url.searchParams.set(TRACKER_PARAM, tracker);
		else url.searchParams.delete(TRACKER_PARAM);
		replaceState(url, page.state);
	});

	function openIssues(tracker: IssueTracker) {
		trackerFilter = tracker.id;
		activeTab = 'issues';
	}

	$effect(() => {
		if (!browser || !inFlight) return;
		const id = project?.id;
		if (!id) return;
		const timer = setInterval(() => {
			if (!document.hidden) void issueTrackers.loadProject(id, true);
		}, POLL_MS);
		return () => clearInterval(timer);
	});

	function openConnect(row: IssueTracker | null) {
		editing = row;
		connectOpen = true;
	}

	function openRoute(row: TrackerRoute | null) {
		editingRoute = row;
		routeOpen = true;
	}

	async function test(tracker: IssueTracker) {
		testing = tracker.id;
		try {
			const result = await issueTrackersApi.test(tracker.id);
			if (result.success) toast.success(result.message);
			else toast.error(result.message);
			await issueTrackers.load(true);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Connection not tested');
		} finally {
			testing = null;
		}
	}

	async function toggle(tracker: IssueTracker) {
		try {
			issueTrackers.upsert(
				await issueTrackersApi.update(tracker.id, { is_active: !tracker.is_active })
			);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Tracker not updated');
		}
	}

	async function retry(issue: TrackedIssue) {
		try {
			issueTrackers.upsertIssue(await issueTrackersApi.retry(issue.id));
			toast.success('Issue queued for filing');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Issue not queued');
		}
	}

	async function refresh(issue: TrackedIssue) {
		try {
			issueTrackers.upsertIssue(await issueTrackersApi.refresh(issue.id));
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Status not refreshed');
		}
	}

	async function confirm() {
		const asking = pending;
		if (!asking) return;
		removing = true;
		try {
			if (asking.kind === 'tracker') {
				await issueTrackersApi.remove(asking.tracker.id);
				issueTrackers.drop(asking.tracker.id);
				toast.success(`${asking.tracker.name} removed`);
			} else if (asking.kind === 'route') {
				await issueTrackersApi.removeRoute(asking.route.id);
				issueTrackers.dropRoute(asking.route.id);
				toast.success('Route removed');
			} else {
				await issueTrackersApi.unlink(asking.issue.id);
				issueTrackers.dropIssue(asking.issue.id);
				toast.success('Issue unlinked');
			}
			pending = null;
		} catch (e) {
			const fallback =
				asking.kind === 'tracker'
					? 'Tracker not removed'
					: asking.kind === 'route'
						? 'Route not removed'
						: 'Issue not unlinked';
			toast.error(e instanceof Error ? e.message : fallback);
		} finally {
			removing = false;
		}
	}

	let asked = $state<Pending | null>(null);
	$effect(() => {
		if (pending) asked = pending;
	});

	const confirmCopy = $derived.by(() => {
		if (!asked) return { title: '', body: '', label: '', busy: '' };
		if (asked.kind === 'tracker') {
			return {
				title: 'Remove tracker',
				body: `Tracker ${asked.tracker.name}, its routes and its issue links are removed.`,
				label: 'Remove',
				busy: 'Removing'
			};
		}
		if (asked.kind === 'route') {
			const scope = asked.route.target_value ?? `every target in ${project?.name ?? ''}`;
			return {
				title: 'Remove route',
				body: `Route for ${scope} is removed.`,
				label: 'Remove',
				busy: 'Removing'
			};
		}
		const i = asked.issue;
		return {
			title: 'Unlink issue',
			body: `Link between ${i.external_key ?? i.title} and ${plural(i.findings, 'finding')} is removed.`,
			label: 'Unlink',
			busy: 'Unlinking'
		};
	});
</script>

<svelte:head><title>{pageTitle(routeLabels['issue-trackers'])}</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-3">
		<div class="min-w-0">
			<h1 class="text-2xl font-semibold tracking-tight">{routeLabels['issue-trackers']}</h1>
		</div>
		{#if canAdmin}
			<div class="flex flex-wrap items-center gap-2">
				{#if tab === 'routes' && trackers.length}
					<Button size="sm" variant="outline" onclick={() => openRoute(null)}>
						<PlusIcon class="size-4" />
						Add route
					</Button>
				{/if}
				<Hint text={atLimit ? `Limit of ${MAX_TRACKERS} trackers reached.` : ''}>
					{#snippet child(props)}
						<span {...props} class="inline-flex">
							<Button size="sm" disabled={atLimit} onclick={() => openConnect(null)}>
								<PlusIcon class="size-4" />
								Connect a tracker
							</Button>
						</span>
					{/snippet}
				</Hint>
			</div>
		{/if}
	</div>

	{#if !issueTrackers.loaded && issueTrackers.error}
		<EmptyState
			icon={TriangleAlertIcon}
			title="Issue trackers not loaded"
			description={issueTrackers.error}
		>
			<Button size="sm" variant="outline" onclick={() => issueTrackers.load(true)}>Retry</Button>
		</EmptyState>
	{:else if !issueTrackers.loaded}
		<Card.Root class="gap-3 p-4">
			<Skeleton class="h-8 w-full" />
			<Skeleton class="h-10 w-full" />
			<Skeleton class="h-10 w-full" />
		</Card.Root>
	{:else if !trackers.length}
		<EmptyState icon={SquareKanbanIcon} title="No issue trackers">
			{#if canAdmin}
				<Button size="sm" onclick={() => openConnect(null)}>
					<PlusIcon class="size-4" />
					Connect a tracker
				</Button>
			{/if}
		</EmptyState>
	{:else}
		<Card.Root class="gap-0 overflow-hidden py-0">
			<div class="border-b px-2">
				<CountTabs
					tabs={TABS}
					value={tab}
					{counts}
					capped={{ issues: issueTrackers.issuesCapped }}
					onChange={(k) => (activeTab = k as IssueTrackerTab)}
				/>
			</div>
			{#if tab === 'issues'}
				{#if issueTrackers.issuesError}
					<EmptyState
						icon={TriangleAlertIcon}
						title="Issues not loaded"
						description={issueTrackers.issuesError}
						class="rounded-none border-0 bg-transparent py-16"
					>
						{#if project}
							<Button
								size="sm"
								variant="outline"
								onclick={() => issueTrackers.loadProject(project.id, true)}
							>
								Retry
							</Button>
						{/if}
					</EmptyState>
				{:else if issueTrackers.issuesLoading && !issueTrackers.issues.length}
					<div class="flex flex-col gap-2 p-4">
						<Skeleton class="h-10 w-full" />
						<Skeleton class="h-10 w-full" />
					</div>
				{:else}
					<FilterChips
						chips={filterChips}
						onRemove={() => (trackerFilter = null)}
						onClear={() => (trackerFilter = null)}
					/>
					{#if !shownIssues.length}
						<EmptyState
							icon={SquareKanbanIcon}
							title="No issues filed"
							class="rounded-none border-0 bg-transparent py-16"
						/>
					{:else}
						<IssuesTable
							issues={shownIssues}
							onRetry={retry}
							onRefresh={refresh}
							onUnlink={(issue) => (pending = { kind: 'issue', issue })}
						/>
					{/if}
				{/if}
			{:else if tab === 'trackers'}
				<TrackersTable
					{trackers}
					issues={issueTrackers.issues}
					capped={issueTrackers.issuesCapped}
					{canAdmin}
					{testing}
					onEdit={(t) => openConnect(t)}
					onTest={test}
					onToggle={toggle}
					onRemove={(tracker) => (pending = { kind: 'tracker', tracker })}
					onOpenIssues={openIssues}
				/>
			{:else if !issueTrackers.routes.length}
				<EmptyState
					icon={SquareKanbanIcon}
					title="No routes"
					class="rounded-none border-0 bg-transparent py-16"
				>
					{#if canAdmin}
						<Button size="sm" variant="outline" onclick={() => openRoute(null)}>
							<PlusIcon class="size-4" />
							Add route
						</Button>
					{/if}
				</EmptyState>
			{:else}
				<RoutesTable
					routes={issueTrackers.routes}
					{trackers}
					projectName={project?.name ?? ''}
					{canAdmin}
					onEdit={(r) => openRoute(r)}
					onRemove={(route) => (pending = { kind: 'route', route })}
				/>
			{/if}
		</Card.Root>
	{/if}
</div>

{#if canAdmin}
	<ConnectSheet bind:open={connectOpen} {editing} />
	<RouteDialog bind:open={routeOpen} editing={editingRoute} />
{/if}

<ConfirmDialog
	open={pending !== null}
	title={confirmCopy.title}
	description={confirmCopy.body}
	confirmLabel={confirmCopy.label}
	loadingLabel={confirmCopy.busy}
	destructive
	loading={removing}
	onOpenChange={(v) => {
		if (!v) pending = null;
	}}
	onConfirm={confirm}
/>
