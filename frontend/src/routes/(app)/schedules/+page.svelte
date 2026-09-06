<script lang="ts">
	import { untrack } from 'svelte';
	import { toast } from 'svelte-sonner';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Plus from '@lucide/svelte/icons/plus';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';

	import { scanSchedulesStore } from '$lib/stores/scan-schedules.svelte';
	import { projectsStore } from '$lib/stores/projects.svelte';
	import { instanceSettingsStore } from '$lib/stores/instanceSettings.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import EmptyState from '@/components/empty-state.svelte';
	import ScheduleListCard from '$lib/components/schedules/schedule-list-card.svelte';
	import ScheduleModal from '$lib/components/schedules/schedule-modal.svelte';
	import DeleteConfirmationDialog from '@/components/delete-confirmation-dialog.svelte';
	import type { ScanScheduleRead } from '$lib/types/scan-schedule';

	let isRefreshing = $state(false);
	let showModal = $state(false);
	let editing = $state<ScanScheduleRead | null>(null);
	let scheduleToDelete = $state<ScanScheduleRead | null>(null);
	let showDeleteDialog = $state(false);
	let isDeleting = $state(false);

	$effect(() => {
		const project = projectsStore.activeProject;
		const hasFetched = projectsStore.hasFetched;
		if (project && hasFetched) {
			untrack(() => {
				if (scanSchedulesStore.fetchedProjectId !== project.id) {
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
			toast.error('No active project selected');
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
			toast.success(`Launched ${count} scan${count === 1 ? '' : 's'}`);
		} else {
			toast.error(scanSchedulesStore.error ?? 'Schedule could not be started');
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
			toast.error(scanSchedulesStore.error ?? 'Schedule could not be updated');
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
				toast.success(`Deleted "${scheduleToDelete.name}"`);
				showDeleteDialog = false;
				scheduleToDelete = null;
			} else {
				toast.error(scanSchedulesStore.error ?? 'Schedule could not be deleted');
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
			if (scanSchedulesStore.error) {
				toast.error(scanSchedulesStore.error);
			} else {
				toast.success('Refreshed');
			}
		} finally {
			isRefreshing = false;
		}
	}
</script>

<div class="space-y-6">
	<div class="flex items-start justify-between">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight">Schedules</h1>
			<p class="mt-1 text-sm text-muted-foreground">Recurring and one-off scans in this project</p>
		</div>
		<div class="flex items-center gap-2">
			<Button
				variant="outline"
				size="icon"
				class="h-9 w-9"
				onclick={handleRefresh}
				disabled={isRefreshing}
			>
				<RefreshCw class="h-4 w-4 {isRefreshing ? 'animate-spin' : ''}" />
			</Button>
			<Button onclick={handleNew} class="gap-2">
				<Plus class="h-4 w-4" />
				New schedule
			</Button>
		</div>
	</div>

	{#if scanSchedulesStore.error && !scanSchedulesStore.isLoading}
		<div
			class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive"
		>
			{scanSchedulesStore.error}
		</div>
	{/if}

	{#if scanSchedulesStore.isLoading}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each Array(3) as _, i (i)}
				<Skeleton class="h-[170px] rounded-lg" />
			{/each}
		</div>
	{:else if scanSchedulesStore.schedules.length === 0}
		<EmptyState
			icon={CalendarClock}
			title="No scheduled scans yet"
			description="Run a scan once at a set time, or repeat it hourly, daily or on a cron expression."
		>
			<Button onclick={handleNew} class="gap-2">
				<Plus size={15} />
				Schedule a scan
			</Button>
		</EmptyState>
	{:else}
		<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each scanSchedulesStore.schedules as schedule (schedule.id)}
				<ScheduleListCard
					{schedule}
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
				: ''} in this project
		</p>
	{/if}
</div>

<ScheduleModal bind:open={showModal} schedule={editing} onClose={() => (editing = null)} />

{#if scheduleToDelete}
	<DeleteConfirmationDialog
		bind:open={showDeleteDialog}
		title="Delete this schedule?"
		description="The schedule stops running. Scans it already launched are kept. This action cannot be undone."
		{isDeleting}
		onOpenChange={(open) => {
			showDeleteDialog = open;
			if (!open) scheduleToDelete = null;
		}}
		onConfirm={confirmDelete}
	/>
{/if}
