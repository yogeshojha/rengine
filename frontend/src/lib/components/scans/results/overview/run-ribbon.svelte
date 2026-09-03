<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Circle from '@lucide/svelte/icons/circle';
	import Ban from '@lucide/svelte/icons/ban';
	import * as Tooltip from '$lib/components/ui/tooltip';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Spinner } from '$lib/components/ui/spinner';
	import StageDialog from './stage-dialog.svelte';
	import {
		durationLabel,
		durationText,
		formatSeconds,
		isLiveStatus
	} from '$lib/utilities/scan-status';
	import { plannedStages, stageRows } from '$lib/utilities/scan-progress';
	import type { StageStepState } from '$lib/utilities/scan-progress';
	import { targetTypeLabel } from '$lib/types/scan-engine';
	import { cn } from '$lib/utils';
	import type { ScanActivityRead, ScanCommandRead, ScanRead } from '$lib/types/scan';
	import type { StageCatalogEntry } from '$lib/types/scan-engine';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';

	interface Props {
		scan: ScanRead;
		run: LiveRun | undefined;
		catalog: StageCatalogEntry[];
		activities: ScanActivityRead[];
		commands: ScanCommandRead[];
		now: number;
		previousDuration: number | null;
		scanId: string;
		projectId: string;
		class?: string;
	}

	let {
		scan,
		run,
		catalog,
		activities,
		commands,
		now,
		previousDuration,
		scanId,
		projectId,
		class: className
	}: Props = $props();

	const FLOOR_SHARE = 0.03;
	const FALLBACK_SECONDS = 30;
	const INSIGHT_SHARE = 0.5;
	const FILL: Record<'done' | 'running' | 'failed' | 'stopped' | 'pending', string> = {
		done: 'var(--chart-1)',
		running: 'var(--info)',
		failed: 'var(--destructive)',
		stopped: 'var(--warning)',
		pending: 'color-mix(in oklch, var(--muted-foreground) 25%, transparent)'
	};
	const fmtTime = (iso: string) =>
		new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

	interface Segment {
		name: string;
		title: string;
		state: StageStepState;
		stopped: boolean;
		seconds: number | null;
		weight: number;
		fill: string;
		startedAt: string | null;
		hasActivity: boolean;
	}

	let live = $derived(isLiveStatus(scan.status));
	let planned = $derived(plannedStages(scan, catalog));
	let byName = $derived(new Map(activities.map((a) => [a.name, a])));
	let rows = $derived(stageRows(planned, activities, run));
	let done = $derived(rows.filter((r) => r.state === 'done').length);
	let skipped = $derived(activities.filter((a) => a.status === 'skipped').length);
	let typeLabel = $derived(targetTypeLabel(scan.execution_config.target_type).toLowerCase());

	let segments = $derived.by<Segment[]>(() => {
		const measured = rows.map((r) => {
			const a = byName.get(r.name);
			let seconds: number | null = null;
			if (r.state === 'running')
				seconds = a?.started_at ? Math.max(0, (now - Date.parse(a.started_at)) / 1000) : 0;
			else if (r.state !== 'pending') seconds = a?.duration_seconds ?? 0;
			return { r, a, seconds };
		});
		const known = measured.flatMap((m) => (m.seconds == null ? [] : [m.seconds]));
		const spent = known.reduce((n, s) => n + s, 0);
		const pendingCount = measured.length - known.length;
		const average = known.length ? spent / known.length : FALLBACK_SECONDS;
		const remaining = previousDuration != null ? Math.max(0, previousDuration - spent) : 0;
		const estimate = live ? (remaining > 0 ? remaining / pendingCount : average) : 0;
		const total = spent + estimate * pendingCount;
		const floor = total > 0 ? total * FLOOR_SHARE : 1;
		return measured.map(({ r, a, seconds }) => {
			const stopped = a?.status === 'aborted';
			const fill = r.state === 'failed' ? (stopped ? FILL.stopped : FILL.failed) : FILL[r.state];
			return {
				name: r.name,
				title: r.title,
				state: r.state,
				stopped,
				seconds,
				weight: Math.max(floor, seconds ?? estimate),
				fill,
				startedAt: a?.started_at ?? null,
				hasActivity: !!a
			};
		});
	});

	let caption = $derived.by(() => {
		if (!rows.length) return '';
		const dur = durationLabel(scan, now);
		const parts: string[] = [];
		switch (scan.status) {
			case 'pending':
				parts.push(`${rows.length} stages queued`);
				break;
			case 'running':
				return '';
			case 'failed': {
				const failed = rows.find((r) => r.state === 'failed');
				parts.push(failed ? `Failed at ${failed.title} after ${dur}` : `Failed after ${dur}`);
				break;
			}
			case 'cancelled':
				parts.push(`Stopped after ${done} of ${rows.length} stages · ${dur}`);
				break;
			default: {
				parts.push(
					done === rows.length
						? `All ${rows.length} stages completed in ${dur}`
						: `${done} of ${rows.length} stages completed in ${dur}`
				);
				const spent = segments.reduce((n, s) => n + (s.seconds ?? 0), 0);
				const top = segments.reduce<Segment | null>(
					(best, s) => (s.state === 'done' && (s.seconds ?? 0) > (best?.seconds ?? 0) ? s : best),
					null
				);
				if (top && rows.length > 1 && spent > 0 && (top.seconds ?? 0) / spent >= INSIGHT_SHARE)
					parts.push(
						`${top.title} took ${Math.round(((top.seconds ?? 0) / spent) * 100)}% of the total time`
					);
			}
		}
		if (skipped > 0)
			parts.push(
				`${skipped} ${skipped === 1 ? 'stage does' : 'stages do'} not apply to a ${typeLabel} target`
			);
		return parts.join(' · ');
	});

	function tooltip(s: Segment): string {
		const parts = [s.title];
		if (s.startedAt) parts.push(fmtTime(s.startedAt));
		if (s.state === 'running') parts.push(`running ${formatSeconds(s.seconds ?? 0)}`);
		else if (s.state === 'pending') parts.push(live ? 'queued' : 'did not run');
		else if (s.state === 'failed') parts.push(s.stopped ? 'stopped' : 'failed');
		else parts.push(durationText(s.seconds));
		return parts.join(' · ');
	}

	let hovered = $state<string | null>(null);
	let selected = $state<string | null>(null);
	let dialogOpen = $state(false);
	let selectedActivity = $derived(selected ? (byName.get(selected) ?? null) : null);
	let selectedCommands = $derived(
		selectedActivity ? commands.filter((c) => c.activity_id === selectedActivity.id) : []
	);
	let selectedEntry = $derived(planned.find((s) => s.name === selected));

	function select(s: Segment) {
		if (!s.hasActivity) return;
		selected = s.name;
		dialogOpen = true;
	}
</script>

<div class={cn('flex flex-col gap-2.5', className)}>
	{#if !catalog.length}
		<Skeleton class="h-1.5 w-full" />
		<Skeleton class="h-5 w-2/3" />
	{:else}
		<div class="flex h-1.5 w-full gap-0.5" role="img" aria-label="Time spent per stage">
			{#each segments as s (s.name)}
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<button
								{...props}
								type="button"
								class="relative h-full min-w-1.5 rounded-full transition-opacity before:absolute before:inset-x-0 before:-inset-y-1 before:content-[''] {s.state ===
								'running'
									? 'animate-pulse'
									: ''} {hovered && hovered !== s.name ? 'opacity-40' : ''} {s.hasActivity
									? 'cursor-pointer'
									: 'cursor-default'}"
								style="flex:{s.weight} 1 0;background:{s.fill}"
								aria-label={tooltip(s)}
								onclick={() => select(s)}
								onpointerenter={() => (hovered = s.name)}
								onpointerleave={() => (hovered = null)}
							></button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="top">{tooltip(s)}</Tooltip.Content>
				</Tooltip.Root>
			{/each}
		</div>

		<div class="-ml-1.5 flex flex-wrap items-center gap-y-1">
			{#each segments as s, i (s.name)}
				{#if i > 0}
					<span class="link" aria-hidden="true"></span>
				{/if}
				<button
					type="button"
					class="flex h-6 items-center gap-1.5 rounded-md px-1.5 text-xs transition-colors {hovered ===
					s.name
						? 'bg-muted/60'
						: ''} {s.hasActivity ? 'cursor-pointer hover:bg-muted/60' : 'cursor-default'}"
					disabled={!s.hasActivity}
					onclick={() => select(s)}
					onpointerenter={() => (hovered = s.name)}
					onpointerleave={() => (hovered = null)}
				>
					<span class="flex size-3.5 shrink-0 items-center justify-center">
						{#if s.state === 'done'}
							<CircleCheck class="size-3.5 text-success" />
						{:else if s.state === 'failed' && s.stopped}
							<Ban class="size-3.5 text-warning" />
						{:else if s.state === 'failed'}
							<CircleX class="size-3.5 text-destructive" />
						{:else if s.state === 'running'}
							<Spinner class="size-3.5 text-info" />
						{:else}
							<Circle class="size-3.5 text-muted-foreground/40" />
						{/if}
					</span>
					<span class={s.state === 'pending' ? 'text-muted-foreground' : ''}>{s.title}</span>
					{#if s.seconds != null}
						<span class="text-muted-foreground tabular-nums">
							{s.state === 'running' ? formatSeconds(s.seconds) : durationText(s.seconds)}
						</span>
					{/if}
				</button>
			{/each}
		</div>

		{#if caption}
			<p class="text-xs text-muted-foreground">{caption}</p>
		{/if}
	{/if}
</div>

<StageDialog
	bind:open={dialogOpen}
	title={selectedEntry?.title ?? ''}
	description={selectedEntry?.description ?? ''}
	activity={selectedActivity}
	commands={selectedCommands}
	{scanId}
	{projectId}
/>

<style>
	.link {
		width: 14px;
		height: 3px;
		margin: 0 2px;
		background: radial-gradient(
				circle,
				color-mix(in oklch, var(--muted-foreground) 65%, transparent) 1px,
				transparent 1.6px
			)
			center / 5px 3px repeat-x;
	}
</style>
