<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Spinner } from '$lib/components/ui/spinner/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import Hint from '$lib/components/hint.svelte';
	import Clock from '@lucide/svelte/icons/clock';
	import Ban from '@lucide/svelte/icons/ban';
	import { ROUTES } from '$lib/config/routes';
	import { elapsedSeconds, formatSeconds, scanCountPills } from '$lib/utilities/scan-status';
	import {
		STAGE_STEP_CLASS,
		etaLabel,
		plannedStages,
		stageProgress
	} from '$lib/utilities/scan-progress';
	import type { ScanRead } from '$lib/types/scan';
	import type { StageCatalogEntry } from '$lib/types/scan-engine';
	import type { LiveRun } from '$lib/stores/live-scans.svelte';

	interface Props {
		scan: ScanRead;
		run?: LiveRun;
		catalog: StageCatalogEntry[];
		previousDuration?: number | null;
		now: number;
		onNavigate?: () => void;
		onCancel?: (scan: ScanRead) => void;
	}

	let { scan, run, catalog, previousDuration = null, now, onNavigate, onCancel }: Props = $props();

	let queued = $derived(scan.status === 'pending');
	let elapsedSec = $derived(elapsedSeconds(scan, now));
	let elapsed = $derived(elapsedSec == null ? null : formatSeconds(elapsedSec));
	let eta = $derived(queued ? null : etaLabel(previousDuration, elapsedSec));
	let planned = $derived(plannedStages(scan, catalog));
	let progress = $derived(stageProgress(scan, run, planned));
	let pills = $derived(scanCountPills(scan).filter((p) => p.value > 0));
	let failed = $derived(run?.failed.length ?? 0);
	let subtitle = $derived(
		run?.message ?? `${scan.engine_name}${scan.context_name ? ` · ${scan.context_name}` : ''}`
	);
</script>

<div
	class="group/card relative rounded-md border border-border bg-card/60 transition-colors hover:border-info/40"
>
	<a href={ROUTES.scan(scan.id)} onclick={onNavigate} class="block p-2.5">
		<div class="flex items-center gap-2">
			{#if queued}
				<Clock class="size-3.5 shrink-0 text-muted-foreground" />
			{:else}
				<Spinner class="size-3.5 shrink-0 text-info" />
			{/if}
			<span class="min-w-0 flex-1 truncate font-mono text-[12px] font-medium text-foreground">
				{scan.execution_config.target_value}
			</span>
			{#if elapsed}
				<span
					class="flex shrink-0 items-center gap-1 font-mono text-[10px] text-muted-foreground tabular-nums transition-opacity group-hover/card:opacity-0"
				>
					{elapsed}
					{#if eta}
						<span class="text-muted-foreground/60">· {eta}</span>
					{/if}
				</span>
			{/if}
		</div>

		{#if !queued && progress.steps.length > 0}
			<div class="mt-2 flex items-center gap-2">
				<div
					class="flex flex-1 gap-[3px]"
					role="img"
					aria-label="{progress.done} of {progress.total} stages done"
				>
					{#each progress.steps as step (step.name)}
						<Hint text={step.title}>
							{#snippet child(props)}
								<span {...props} class="h-1 flex-1 rounded-full {STAGE_STEP_CLASS[step.state]}"
								></span>
							{/snippet}
						</Hint>
					{/each}
				</div>
				<span class="shrink-0 font-mono text-[10px] text-muted-foreground tabular-nums">
					{progress.done}/{progress.total}
				</span>
			</div>
		{/if}

		<div class="mt-1.5 flex min-w-0 items-center gap-1.5">
			<span class="truncate text-[11px] font-medium text-foreground/90">{progress.label}</span>
			{#if run?.tool}
				<span
					class="shrink-0 rounded bg-muted px-1 py-px font-mono text-[10px] text-muted-foreground"
				>
					{run.tool}
				</span>
			{/if}
		</div>
		<p class="mt-0.5 truncate text-[10px] text-muted-foreground">{subtitle}</p>

		{#if pills.length > 0 || failed > 0}
			<div class="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-0.5">
				{#each pills as p (p.key)}
					<Hint text={p.label}>
						{#snippet child(props)}
							<span
								{...props}
								class="inline-flex items-center gap-1 text-[10px] tabular-nums {p.emphasis
									? 'font-medium text-warning'
									: 'text-muted-foreground'}"
							>
								<p.icon class="size-3" />
								{p.value}
							</span>
						{/snippet}
					</Hint>
				{/each}
				{#if failed > 0}
					<span class="text-[10px] font-medium text-destructive">
						{failed} stage{failed === 1 ? '' : 's'} failed
					</span>
				{/if}
			</div>
		{/if}
	</a>

	{#if onCancel}
		<Tooltip.Root>
			<Tooltip.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="ghost"
						size="icon-sm"
						class="absolute top-1.5 right-1.5 size-6 text-muted-foreground opacity-0 group-hover/card:opacity-100 hover:text-destructive focus-visible:opacity-100"
						aria-label="Cancel scan"
						onclick={() => onCancel(scan)}
					>
						<Ban class="size-3" />
					</Button>
				{/snippet}
			</Tooltip.Trigger>
			<Tooltip.Content side="left">Cancel scan</Tooltip.Content>
		</Tooltip.Root>
	{/if}
</div>
