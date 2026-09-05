<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import CircleX from '@lucide/svelte/icons/circle-x';
	import Circle from '@lucide/svelte/icons/circle';
	import CircleSlash from '@lucide/svelte/icons/circle-slash';
	import Ban from '@lucide/svelte/icons/ban';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import * as Collapsible from '$lib/components/ui/collapsible';
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
	const MIN_METER = 4;
	const FILL: Record<'done' | 'running' | 'failed' | 'stopped' | 'partial' | 'pending', string> = {
		done: 'var(--chart-1)',
		running: 'var(--info)',
		failed: 'var(--destructive)',
		stopped: 'var(--warning)',
		partial: 'var(--warning)',
		pending: 'color-mix(in oklch, var(--muted-foreground) 25%, transparent)'
	};
	const fmtTime = (iso: string) =>
		new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

	interface Segment {
		name: string;
		title: string;
		state: StageStepState;
		stopped: boolean;
		degraded: boolean;
		seconds: number | null;
		weight: number;
		fill: string;
		startedAt: string | null;
		hasActivity: boolean;
		summary: string;
		error: string | null;
	}

	let live = $derived(isLiveStatus(scan.status));
	let planned = $derived(plannedStages(scan, catalog));
	let byName = $derived(new Map(activities.map((a) => [a.name, a])));
	let rows = $derived(stageRows(planned, activities, run));
	let done = $derived(rows.filter((r) => r.state === 'done').length);
	let skipped = $derived(activities.filter((a) => a.status === 'skipped'));
	let degradedStages = $derived(activities.filter((a) => a.status === 'partial'));
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
			const degraded = a?.status === 'partial';
			const fill =
				r.state === 'failed'
					? stopped
						? FILL.stopped
						: FILL.failed
					: degraded
						? FILL.partial
						: FILL[r.state];
			return {
				name: r.name,
				title: r.title,
				state: r.state,
				stopped,
				degraded,
				seconds,
				weight: Math.max(floor, seconds ?? estimate),
				fill,
				startedAt: a?.started_at ?? null,
				hasActivity: !!a,
				summary: r.summary,
				error: r.error
			};
		});
	});

	let slowest = $derived(segments.reduce((n, s) => Math.max(n, s.seconds ?? 0), 0));

	let caption = $derived.by(() => {
		if (!rows.length) return '';
		const dur = durationLabel(scan, now);
		const parts: string[] = [];
		switch (scan.status) {
			case 'pending':
				parts.push(`${rows.length} stages queued`);
				break;
			case 'running': {
				const left = rows.length - done;
				parts.push(
					left > 0 ? `${left} ${left === 1 ? 'stage' : 'stages'} remaining` : 'All stages completed'
				);
				break;
			}
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
		if (degradedStages.length > 0)
			parts.push(
				`${degradedStages.length} ${degradedStages.length === 1 ? 'stage' : 'stages'} finished with less than the full result`
			);
		if (skipped.length > 0)
			parts.push(
				`${skipped.length} ${skipped.length === 1 ? 'stage does' : 'stages do'} not apply to a ${typeLabel} target`
			);
		return parts.join(' · ');
	});

	function tooltip(s: Segment): string {
		const parts = [s.title];
		if (s.startedAt) parts.push(fmtTime(s.startedAt));
		if (s.state === 'running') parts.push(`running ${formatSeconds(s.seconds ?? 0)}`);
		else if (s.state === 'pending') parts.push(live ? 'queued' : 'did not run');
		else if (s.state === 'failed') parts.push(s.stopped ? 'stopped' : 'failed');
		else if (s.degraded) parts.push(`${durationText(s.seconds)} · partial`);
		else parts.push(durationText(s.seconds));
		return parts.join(' · ');
	}

	let open = $state(false);

	let hovered = $state<string | null>(null);
	let selected = $state<string | null>(null);
	let dialogOpen = $state(false);
	let selectedActivity = $derived(selected ? (byName.get(selected) ?? null) : null);
	let selectedCommands = $derived(
		selectedActivity ? commands.filter((c) => c.activity_id === selectedActivity.id) : []
	);
	let selectedEntry = $derived(catalog.find((s) => s.name === selected));

	function select(name: string, hasActivity: boolean) {
		if (!hasActivity) return;
		selected = name;
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
								onclick={() => select(s.name, s.hasActivity)}
								onpointerenter={() => (hovered = s.name)}
								onpointerleave={() => (hovered = null)}
							></button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content side="top">{tooltip(s)}</Tooltip.Content>
				</Tooltip.Root>
			{/each}
		</div>

		{#if caption}
			<Collapsible.Root bind:open>
				<Collapsible.Trigger
					class="group -mx-1.5 flex max-w-full cursor-pointer items-center gap-1.5 rounded-md px-1.5 py-1 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
				>
					<span class="min-w-0">{caption}</span>
					<span class="flex h-4 shrink-0 items-center">
						<ChevronDown class="size-3.5 transition-transform group-data-[state=open]:rotate-180" />
					</span>
				</Collapsible.Trigger>

				<Collapsible.Content
					class="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down"
				>
					<ul class="-mx-2 mt-1 flex flex-col">
						{#each segments as s (s.name)}
							<li>
								<button
									type="button"
									class="flex w-full items-start gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors {hovered ===
									s.name
										? 'bg-muted/60'
										: ''} {s.hasActivity ? 'cursor-pointer' : 'cursor-default'}"
									disabled={!s.hasActivity}
									onclick={() => select(s.name, s.hasActivity)}
									onpointerenter={() => (hovered = s.name)}
									onpointerleave={() => (hovered = null)}
								>
									<span class="flex h-5 shrink-0 items-center">
										{#if s.degraded}
											<TriangleAlert class="size-3.5 text-warning" />
										{:else if s.state === 'done'}
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
									<span class="flex min-w-0 flex-1 flex-col">
										<span
											class="text-sm leading-5 {s.state === 'pending'
												? 'text-muted-foreground'
												: ''}"
										>
											{s.title}
										</span>
										{#if s.summary}
											<span class="text-xs leading-4 text-muted-foreground">{s.summary}</span>
										{/if}
										{#if s.error}
											<span class="text-xs leading-4 break-words text-destructive">{s.error}</span>
										{/if}
									</span>
									{#if s.seconds != null && slowest > 0}
										<span class="hidden h-5 w-24 shrink-0 items-center sm:flex">
											<span class="h-1 w-full overflow-hidden rounded-full bg-muted">
												<span
													class="block h-full rounded-full"
													style="width:{Math.max(
														MIN_METER,
														(s.seconds / slowest) * 100
													)}%;background:{s.fill}"
												></span>
											</span>
										</span>
									{:else}
										<span class="hidden h-5 w-24 shrink-0 sm:block"></span>
									{/if}
									<span
										class="flex h-5 w-14 shrink-0 items-center justify-end text-xs text-muted-foreground tabular-nums"
									>
										{#if s.state === 'running'}
											{formatSeconds(s.seconds ?? 0)}
										{:else if s.state === 'pending'}
											{live ? 'Queued' : '—'}
										{:else}
											{durationText(s.seconds)}
										{/if}
									</span>
								</button>
							</li>
						{/each}

						{#each skipped as a (a.id)}
							<li>
								<button
									type="button"
									class="flex w-full cursor-pointer items-start gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-muted/60"
									onclick={() => select(a.name, true)}
								>
									<span class="flex h-5 shrink-0 items-center">
										<CircleSlash class="size-3.5 text-muted-foreground/40" />
									</span>
									<span class="min-w-0 flex-1 text-sm leading-5 text-muted-foreground">
										{catalog.find((s) => s.name === a.name)?.title ?? a.name}
									</span>
									<span class="hidden h-5 w-24 shrink-0 sm:block"></span>
									<span
										class="flex h-5 w-14 shrink-0 items-center justify-end text-xs text-muted-foreground"
									>
										Skipped
									</span>
								</button>
							</li>
						{/each}
					</ul>
				</Collapsible.Content>
			</Collapsible.Root>
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
