<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Pause from '@lucide/svelte/icons/pause';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Play from '@lucide/svelte/icons/play';
	import Radar from '@lucide/svelte/icons/radar';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Hint from '$lib/components/hint.svelte';
	import { relativeTime } from '$lib/utilities/dates';
	import { plural } from '$lib/utilities/strings';
	import { SCHEDULE_STATUS_LABELS, type ScanScheduleRead } from '$lib/types/scan-schedule';

	interface Props {
		schedule: ScanScheduleRead;
		checked?: boolean;
		onCheck?: (id: string) => void;
		onEdit?: () => void;
		onRunNow?: () => void;
		onTogglePause?: () => void;
		onDelete?: () => void;
	}

	let {
		schedule,
		checked = false,
		onCheck,
		onEdit,
		onRunNow,
		onTogglePause,
		onDelete
	}: Props = $props();

	let isPaused = $derived(schedule.status === 'paused');
	let isCompleted = $derived(schedule.status === 'completed');

	function formatNext(iso: string | null): string {
		if (!iso) return '—';
		const date = new Date(iso);
		return new Intl.DateTimeFormat(undefined, {
			timeZone: schedule.timezone,
			year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit',
			hourCycle: 'h23'
		}).format(date);
	}
</script>

<div class="flex flex-col rounded-xl border border-border bg-card p-4">
	<div class="mb-2 flex items-start justify-between gap-2">
		<div class="flex min-w-0 flex-1 items-center gap-2">
			{#if onCheck}
				<Checkbox
					{checked}
					onCheckedChange={() => onCheck(schedule.id)}
					aria-label="Select {schedule.name}"
					class="shrink-0"
				/>
			{/if}
			<h3 class="truncate text-sm leading-5 font-semibold text-foreground">{schedule.name}</h3>
			<Badge
				variant={isPaused ? 'outline' : 'secondary'}
				class={isPaused
					? 'border-warning/40 bg-warning/10 text-2xs font-semibold text-warning'
					: 'text-2xs font-semibold'}
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
					<Radar class="h-4 w-4" /> Run now
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
				<DropdownMenu.Item variant="destructive" onclick={() => onDelete?.()}>
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
			<Hint text="The instance timezone changed. This schedule fires in {schedule.timezone}.">
				{#snippet child(props)}
					<span
						{...props}
						class="shrink-0 rounded border border-warning/30 px-1 text-2xs font-medium text-warning"
					>
						tz changed
					</span>
				{/snippet}
			</Hint>
		{/if}
	</div>

	<div class="mb-3 flex flex-wrap items-center gap-1.5">
		<Badge
			variant="secondary"
			class="rounded-sm border border-border bg-muted px-2 py-0.5 text-2xs font-medium text-muted-foreground"
		>
			{plural(schedule.targets.length || schedule.target_ids.length, 'target')}
		</Badge>
		<Badge
			variant="secondary"
			class="rounded-sm border border-border bg-muted px-2 py-0.5 text-2xs font-medium text-muted-foreground"
		>
			{schedule.engine_name}
		</Badge>
		{#if schedule.context_name}
			<Badge
				variant="secondary"
				class="rounded-sm border border-border bg-muted px-2 py-0.5 text-2xs font-medium text-muted-foreground"
			>
				{schedule.context_name}
			</Badge>
		{/if}
	</div>

	{#if schedule.last_error}
		<Hint text={schedule.last_error}>
			{#snippet child(props)}
				<p {...props} class="mb-2 truncate text-2xs text-destructive">
					Last run error: {schedule.last_error}
				</p>
			{/snippet}
		</Hint>
	{/if}

	<div
		class="mt-auto flex items-center justify-between border-t border-border pt-2.5 text-2xs text-muted-foreground"
	>
		<span>
			{#if isCompleted}
				Completed
			{:else if !isPaused}
				Next: {formatNext(schedule.next_run_at)}
			{/if}
		</span>
		<span>
			{plural(schedule.total_run_count, 'run')}
			{#if schedule.last_run_at}
				· {relativeTime(schedule.last_run_at)}
			{/if}
		</span>
	</div>
</div>
