<script lang="ts">
	import { pageTitle } from '$lib/utilities/page-title';
	import { routeLabels } from '$lib/config/routes';
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';

	import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '$lib/components/empty-state.svelte';
	import Hint from '$lib/components/hint.svelte';
	import PageHeader from '$lib/components/page-header.svelte';
	import ScheduleListCard from '$lib/components/schedules/schedule-list-card.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import SelectionDeleteBar from '$lib/components/selection-delete-bar.svelte';
	import DeleteConfirmationDialog from '$lib/components/delete-confirmation-dialog.svelte';
	import { scanSchedulesApi } from '$lib/api/scan-schedules';
	import { SvelteSet } from 'svelte/reactivity';
	import type { ScanScheduleRead } from '$lib/types/scan-schedule';

	const picked = new SvelteSet<string>();

	function toggleCheck(id: string) {
		if (picked.has(id)) picked.delete(id);
		else picked.add(id);
	}

	let isRefreshing = $state(false);
	let showModal = $state(false);
	let editing = $state<ScanScheduleRead | null>(null);
	let scheduleToDelete = $state<ScanScheduleRead | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);
	let loaded = $derived(
		projectsStore.activeProject
			? scanSchedulesStore.fetchedProjectId === projectsStore.activeProject.id
			: projectsStore.hasFetched
	);
	const empty = $derived(loaded && scanSchedulesStore.schedules.length === 0);

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (scanSchedulesStore.fetchedProjectId !== project.id) {
					picked.clear();
					scanSchedulesStore.fetchSchedules(project.id);
				}
				if (!instanceSettingsStore.hasFetched) {
					instanceSettingsStore.fetch();
				}
			});
		}
	});

	function handleNew() {
		if (!projectsStore.activeProject) {
			toast.error('No active project');
			return;
		}
		editing = null;
		showModal = true;
	}

	function handleEdit(schedule: ScanScheduleRead) {
		editing = schedule;
		showModal = true;
	}

	async function handleRunNow(schedule: ScanScheduleRead) {
		const project = projectsStore.activeProject;
		if (!project) return;
		const count = await scanSchedulesStore.runNow(schedule.id, project.id);
		if (count !== null) {
			toast.success(`${count} scan${count === 1 ? '' : 's'} started`);
		} else {
			toast.error(scanSchedulesStore.error ?? 'Schedule not started');
		}
	}

	async function handleTogglePause(schedule: ScanScheduleRead) {
		const project = projectsStore.activeProject;
		if (!project) return;
		const paused = schedule.status !== 'paused';
		const updated = await scanSchedulesStore.setPaused(schedule.id, project.id, paused);
		if (updated) {
			toast.success(paused ? 'Schedule paused' : 'Schedule resumed');
		} else {
			toast.error(scanSchedulesStore.error ?? 'Schedule not updated');
		}
	}

	function handleDeleteRequest(schedule: ScanScheduleRead) {
		scheduleToDelete = schedule;
		showDeleteDialog = true;
	}

	async function confirmDelete() {
		const project = projectsStore.activeProject;
		if (!scheduleToDelete || !project) return;
		isDeleting = true;
		try {
			const ok = await scanSchedulesStore.deleteSchedule(scheduleToDelete.id, project.id);
			if (ok) {
				toast.success('Schedule deleted');
				picked.delete(scheduleToDelete.id);
				showDeleteDialog = false;
				scheduleToDelete = null;
			} else {
				toast.error(scanSchedulesStore.error ?? 'Schedule not deleted');
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
			await scanSchedulesStore.fetchSchedules(project.id);
			if (scanSchedulesStore.error) toast.error(scanSchedulesStore.error);
		} finally {
			isRefreshing = false;
		}
	}
</script>

<svelte:head><title>{pageTitle(routeLabels.schedules)}</title></svelte:head>

<div class="flex flex-col gap-6">
	<PageHeader title="Schedules" description="Scans that run on a recurring schedule">
		{#snippet actions()}
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
			{#if !empty}
				<Button size="sm" onclick={handleNew}>
					<Plus class="size-4" />
					New schedule
				</Button>
			{/if}
		{/snippet}
	</PageHeader>

	{#if !loaded && scanSchedulesStore.error && !scanSchedulesStore.isLoading}
		<EmptyState
			icon={TriangleAlert}
			title="Schedules not loaded"
			description={scanSchedulesStore.error}
		>
			<Button size="sm" variant="outline" onclick={handleRefresh} disabled={isRefreshing}>
				Retry
			</Button>
		</EmptyState>
	{:else if !loaded}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<div class="flex flex-col gap-3 rounded-xl border border-border p-4">
					<Skeleton class="h-5 w-40" />
					<Skeleton class="h-3.5 w-3/5" />
					<div class="flex gap-1.5">
						<Skeleton class="h-5 w-16" />
						<Skeleton class="h-5 w-24" />
					</div>
					<Skeleton class="mt-2 h-3.5 w-full" />
				</div>
			{/each}
		</div>
	{:else if empty}
		<EmptyState
			icon={CalendarClock}
			title="No schedules"
			description="One-off, hourly, daily or cron."
		>
			<Button size="sm" onclick={handleNew}>
				<Plus class="size-4" />
				New schedule
			</Button>
		</EmptyState>
	{:else}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each scanSchedulesStore.schedules as schedule (schedule.id)}
				<ScheduleListCard
					{schedule}
					checked={picked.has(schedule.id)}
					onCheck={toggleCheck}
					onEdit={() => handleEdit(schedule)}
					onRunNow={() => handleRunNow(schedule)}
					onTogglePause={() => handleTogglePause(schedule)}
					onDelete={() => handleDeleteRequest(schedule)}
				/>
			{/each}
		</div>

		<p class="pt-2 text-center text-xs text-muted-foreground">
			{scanSchedulesStore.schedules.length} schedule{scanSchedulesStore.schedules.length !== 1
				? 's'
				: ''}
		</p>
	{/if}
</div>

<ScheduleModal bind:open={showModal} schedule={editing} onClose={() => (editing = null)} />

{#if scheduleToDelete}
	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete schedule"
		description={`Schedule ${scheduleToDelete.name} is removed.`}
		{isDeleting}
		onOpenChange={(open) => {
			showDeleteDialog = open;
			if (!open) scheduleToDelete = null;
		}}
		onConfirm={confirmDelete}
	/>
{/if}

<SelectionDeleteBar
	ids={[...picked]}
	noun="schedule"
	remove={(id) => scanSchedulesApi.remove(id, projectsStore.activeProject?.id ?? '')}
	onDone={() => {
		picked.clear();
		const project = projectsStore.activeProject;
		if (project) void scanSchedulesStore.fetchSchedules(project.id);
	}}
	onClear={() => picked.clear()}
/>
