<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Pause from '@lucide/svelte/icons/pause';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Play from '@lucide/svelte/icons/play';
	import Rocket from '@lucide/svelte/icons/rocket';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { relativeTime } from '$lib/utilities/dates';
	import { SCHEDULE_STATUS_LABELS, type ScanScheduleRead } from '$lib/types/scan-schedule';

	interface Props {
		schedule: ScanScheduleRead;
		onEdit?: () => void;
		onRunNow?: () => void;
		onTogglePause?: () => void;
		onDelete?: () => void;
	}

	let { schedule, onEdit, onRunNow, onTogglePause, onDelete }: Props = $props();

	let isPaused = $derived(schedule.status === 'paused');
	let isCompleted = $derived(schedule.status === 'completed');

	function formatNext(iso: string | null): string {
		if (!iso) return '—';
		return new Intl.DateTimeFormat(undefined, {
			timeZone: schedule.timezone,
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
			hourCycle: 'h23'
		}).format(new Date(iso));
	}
</script>

<div
	class="group relative flex flex-col rounded-lg border border-border bg-card p-4 shadow-sm transition-shadow hover:shadow-md"
>
	<div class="mb-2 flex items-start justify-between gap-2">
		<div class="flex min-w-0 flex-1 items-center gap-2">
			<h3 class="truncate text-sm font-bold text-foreground">{schedule.name}</h3>
			<Badge
				variant={isPaused ? 'outline' : 'secondary'}
				class={isPaused
					? 'border-warning/40 bg-warning/10 text-[10px] font-semibold text-warning'
					: 'text-[10px] font-semibold'}
			>
				{SCHEDULE_STATUS_LABELS[schedule.status]}
			</Badge>
		</div>
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon"
						class="h-7 w-7 shrink-0"
						aria-label="Actions for {schedule.name}"
					>
						<Ellipsis class="h-4 w-4" />
					</Button>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-44">
				<DropdownMenu.Item onclick={() => onRunNow?.()} class="gap-2">
					<Rocket class="h-4 w-4" /> Run now
				</DropdownMenu.Item>
				<DropdownMenu.Item onclick={() => onEdit?.()} class="gap-2">
					<Pencil class="h-4 w-4" /> Edit
				</DropdownMenu.Item>
				{#if !isCompleted}
					<DropdownMenu.Item onclick={() => onTogglePause?.()} class="gap-2">
						{#if isPaused}
							<Play class="h-4 w-4" /> Resume
						{:else}
							<Pause class="h-4 w-4" /> Pause
						{/if}
					</DropdownMenu.Item>
				{/if}
				<DropdownMenu.Separator />
				<DropdownMenu.Item
					onclick={() => onDelete?.()}
					class="gap-2 text-destructive focus:text-destructive"
				>
					<Trash2 class="h-4 w-4" /> Delete
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>

	<div class="mb-3 flex items-center gap-1.5 text-xs text-muted-foreground">
		<CalendarClock class="h-3.5 w-3.5 shrink-0" />
		<span class="truncate">{schedule.cadence}</span>
		<span class="text-muted-foreground/40">·</span>
		<span class="shrink-0">{schedule.timezone}</span>
		{#if schedule.timezone_stale}
			<span
				class="shrink-0 rounded border border-warning/30 px-1 text-[10px] font-medium text-warning"
				title="The instance timezone changed after this schedule was created; it still fires in {schedule.timezone}."
			>
				tz changed
			</span>
		{/if}
	</div>

	<div class="mb-3 flex flex-wrap items-center gap-1.5">
		<Badge
			variant="secondary"
			class="rounded-sm border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
		>
			{schedule.targets.length || schedule.target_ids.length} target{(schedule.targets.length ||
				schedule.target_ids.length) === 1
				? ''
				: 's'}
		</Badge>
		<Badge
			variant="secondary"
			class="rounded-sm border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
		>
			{schedule.engine_name}
		</Badge>
		{#if schedule.context_name}
			<Badge
				variant="secondary"
				class="rounded-sm border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
			>
				{schedule.context_name}
			</Badge>
		{/if}
	</div>

	{#if schedule.last_error}
		<p class="mb-2 truncate text-[11px] text-destructive" title={schedule.last_error}>
			Last run had errors: {schedule.last_error}
		</p>
	{/if}

	<div
		class="mt-auto flex items-center justify-between border-t border-border pt-2.5 text-[11px] text-muted-foreground"
	>
		<span>
			{#if isCompleted}
				Completed
			{:else}
				Next: {formatNext(schedule.next_run_at)}
			{/if}
		</span>
		<span>
			{schedule.total_run_count} run{schedule.total_run_count === 1 ? '' : 's'}
			{#if schedule.last_run_at}
				· {relativeTime(schedule.last_run_at)}
			{/if}
		</span>
	</div>
</div>
