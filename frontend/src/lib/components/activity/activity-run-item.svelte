<script lang="ts">
	import { goto } from '$app/navigation';
	import { Badge, type BadgeVariant } from '$lib/components/ui/badge/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import Radar from '@lucide/svelte/icons/radar';
	import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import RotateCw from '@lucide/svelte/icons/rotate-cw';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import { relativeTime } from '$lib/utilities/dates';
	import { liveScans } from '$lib/stores/live-scans.svelte';
	import { ROUTES } from '$lib/config/routes';
	import {
		ACTIVITY_EVENT,
		isStageEvent,
		type ActivityCluster,
		type ActivityLog,
		type RunStatus
	} from '$lib/types/activity';

	interface Props {
		cluster: ActivityCluster;
		tick?: number;
		isNew?: boolean;
		inGroup?: boolean;
		onRescan?: (targetId: string) => void;
	}

	let { cluster, tick = 0, isNew = false, inGroup = false, onRescan }: Props = $props();

	const STATUS_LABEL: Record<RunStatus, string> = {
		running: 'Running',
		completed: 'Completed',
		failed: 'Failed',
		cancelled: 'Cancelled'
	};
	const STATUS_VARIANT: Record<RunStatus, BadgeVariant> = {
		running: 'info',
		completed: 'success',
		failed: 'destructive',
		cancelled: 'warning'
	};
	const NODE_TINT: Record<RunStatus, string> = {
		running: 'bg-info/10 text-info ring-1 ring-info/30',
		completed: 'bg-success/10 text-success ring-1 ring-success/30',
		failed: 'bg-destructive/10 text-destructive ring-1 ring-destructive/40',
		cancelled: 'bg-warning/10 text-warning ring-1 ring-warning/30'
	};

	let run = $derived(cluster.run!);
	let live = $derived(!!cluster.scanId && liveScans.isLive(cluster.scanId));
	let status = $derived<RunStatus>(run.status === 'running' && !live ? 'cancelled' : run.status);
	let stageCount = $derived(run.steps.filter((s) => isStageEvent(s.event_type)).length);
	let expanded = $state(false);
	let timeAgo = $derived.by(() => {
		void tick;
		return relativeTime(cluster.timestamp);
	});
	let heading = $derived(inGroup ? `Scan${run.engine ? ` · ${run.engine}` : ''}` : run.target);
	let meta = $derived.by(() => {
		if (run.summary) return run.summary;
		if (status === 'running')
			return stageCount > 0 ? `${stageCount} stage${stageCount === 1 ? '' : 's'} done` : 'Starting';
		return run.engine ?? '';
	});

	function open(e: MouseEvent) {
		e.stopPropagation();
		if (cluster.scanId) goto(ROUTES.scan(cluster.scanId));
	}

	function stepIcon(step: ActivityLog) {
		if (step.event_type === ACTIVITY_EVENT.SCAN_STAGE_FAILED) return CircleX;
		if (step.event_type === ACTIVITY_EVENT.SCAN_STAGE_COMPLETED) return CircleCheck;
		return null;
	}
</script>

<div class="group/item relative flex gap-2.5 pb-3 last:pb-1" class:is-new={isNew}>
	<div class="relative z-[1] flex w-5 shrink-0 justify-center">
		<div class="mt-px flex h-5 w-5 items-center justify-center rounded-full {NODE_TINT[status]}">
			{#if status === 'running'}
				<Spinner class="h-3 w-3" />
			{:else}
				<Radar class="h-3 w-3" />
			{/if}
		</div>
	</div>

	<div class="min-w-0 flex-1">
		<button
			type="button"
			onclick={() => (expanded = !expanded)}
			aria-expanded={expanded}
			class="-ml-1 w-[calc(100%+4px)] cursor-pointer rounded-md px-1.5 py-0.5 text-left transition-colors hover:bg-accent/50"
		>
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0 flex-1">
					<div class="flex min-w-0 items-center gap-1.5">
						<span
							class="truncate text-[12px] leading-tight text-foreground {heading && !inGroup
								? 'font-mono'
								: ''}"
						>
							{heading ?? 'Scan'}
						</span>
						<Badge variant={STATUS_VARIANT[status]} class="h-4 shrink-0 px-1.5 text-[9px]">
							{STATUS_LABEL[status]}
						</Badge>
					</div>
					<p class="mt-0.5 line-clamp-1 text-[10px] text-muted-foreground">
						{#if run.engine && run.summary && !inGroup}
							<span>{run.engine}</span>
							<span class="text-muted-foreground/40"> · </span>
						{/if}
						{meta}
					</p>
				</div>
				<div class="mt-0.5 flex shrink-0 items-center gap-1.5">
					<span class="font-mono text-[10px] text-muted-foreground tabular-nums">{timeAgo}</span>
					{#if isNew}
						<span
							class="new-badge inline-flex h-4 items-center rounded px-1 text-[10px] font-semibold tracking-wide text-chart-1 uppercase"
						>
							new
						</span>
					{/if}
					<ChevronRight
						class="h-3 w-3 text-muted-foreground transition-transform duration-150 {expanded
							? 'rotate-90'
							: ''}"
					/>
				</div>
			</div>
		</button>

		{#if expanded}
			<div class="mt-1 border-l border-border pl-2.5">
				{#if run.steps.length === 0}
					<p class="px-1 py-[3px] text-[10px] text-muted-foreground">No stage events yet.</p>
				{/if}
				{#each run.steps as step (step.id)}
					{@const StepIcon = stepIcon(step)}
					{@const stage = isStageEvent(step.event_type)}
					<div class="flex items-start gap-1.5 px-1 py-[3px] {stage ? '' : 'pl-4'}">
						{#if StepIcon}
							<StepIcon
								class="mt-[3px] h-3 w-3 shrink-0 {step.level === 'error'
									? 'text-destructive'
									: 'text-success'}"
							/>
						{:else}
							<span
								class="mt-[7px] h-1 w-1 shrink-0 rounded-full {step.level === 'error'
									? 'bg-destructive'
									: step.level === 'warning'
										? 'bg-warning'
										: 'bg-muted-foreground/50'}"
							></span>
						{/if}
						<div class="min-w-0 flex-1">
							<p
								class="leading-snug {stage
									? 'text-[11px] text-foreground/85'
									: 'text-[10px] text-muted-foreground'}"
							>
								{step.title}
								{#if step.description}
									<span class="text-muted-foreground">
										{stage ? ' · ' : ' — '}{step.description}
									</span>
								{/if}
							</p>
						</div>
					</div>
				{/each}

				<div class="mt-1 flex items-center gap-1 px-1 pb-0.5">
					{#if cluster.scanId}
						<button
							type="button"
							onclick={open}
							class="inline-flex items-center gap-0.5 rounded px-1 py-0.5 text-[10px] font-medium text-primary hover:bg-primary/10"
						>
							Open scan
							<ArrowUpRight class="h-3 w-3" />
						</button>
					{/if}
					{#if (status === 'failed' || status === 'cancelled') && cluster.targetId && onRescan}
						<button
							type="button"
							onclick={(e) => {
								e.stopPropagation();
								onRescan(cluster.targetId!);
							}}
							class="inline-flex items-center gap-0.5 rounded px-1 py-0.5 text-[10px] font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
						>
							<RotateCw class="h-3 w-3" />
							Rescan
						</button>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.is-new {
		animation:
			slide-in 0.25s ease-out,
			flash 1.4s ease-out;
		border-radius: 6px;
	}
	.new-badge {
		animation: fade-out 5s ease-out forwards;
	}
	@keyframes slide-in {
		from {
			opacity: 0;
			transform: translateY(-3px);
		}
	}
	@keyframes flash {
		0% {
			background-color: color-mix(in oklch, var(--primary) 7%, transparent);
		}
		100% {
			background-color: transparent;
		}
	}
	@keyframes fade-out {
		0%,
		70% {
			opacity: 1;
		}
		100% {
			opacity: 0;
		}
	}
</style>
